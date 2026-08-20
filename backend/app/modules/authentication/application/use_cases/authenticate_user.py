"""`AuthenticateUser` — email/password login for the current frontend's
Sign In page (`POST /auth/login`), producing exactly the response shape
that page already expects: `{access_token, principal}`, where `principal`
is `AuthenticatedPrincipalDTO` (`frontend/src/types/index.ts`'s
`AuthenticatedPrincipal` is a hand-mirrored 1:1 copy of it — see that
file's own comment).

Resolves the user via `UserRepository.get_by_email_any_organization`
(login has no organization field either — see `register_user.py`'s own
docstring for why email is globally unique in this system) rather than
`get_by_email`, which needs an `organization_id` this flow never has.

**Anti-enumeration**: an unknown email and a known email with the wrong
password both raise the same `InvalidCredentialsError` — never anything
that would let a caller distinguish "no such account" from "wrong
password" (see that exception's own docstring). Account-status problems
(`locked`/`suspended`/`deactivated`) are reported with their own specific
exception only *after* the password has already been verified correct —
at that point the caller has proven they hold the credential, so there is
no enumeration risk left in being specific.

Issues a real `UserSession` + `RefreshToken` pair (this module's existing
aggregates, unused until now — see `domain/entities.py`) alongside the
access token, reusing exactly the JWT/session/refresh-token machinery
`ValidateAccessToken`/`app/api/deps.py::get_current_user` already
validates on every authenticated request; this use case is the other half
of that pair (issue vs. validate) that never existed until now.
"""

from datetime import UTC, datetime, timedelta

from app.core.security.jwt import TokenType, encode_token
from app.core.security.password_hashing import verify_password
from app.core.security.token_hashing import generate_raw_refresh_token, hash_refresh_token
from app.modules.authentication.application.dto import (
    AuthenticatedPrincipalDTO,
    AuthenticateUserInput,
    AuthenticateUserOutput,
)
from app.modules.authentication.application.services.permission_service import (
    RbacPermissionService,
)
from app.modules.authentication.domain.entities import RefreshToken, UserSession
from app.modules.authentication.domain.enums import UserStatus
from app.modules.authentication.domain.exceptions import (
    AccountLockedError,
    InactiveAccountError,
    InvalidCredentialsError,
)
from app.modules.authentication.domain.repositories import (
    RefreshTokenRepository,
    UserRepository,
    UserSessionRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase
from app.shared.domain.common_value_objects import EmailAddress


class AuthenticateUser(UseCase[AuthenticateUserInput, AuthenticateUserOutput]):
    def __init__(
        self,
        *,
        user_repository: UserRepository,
        user_session_repository: UserSessionRepository,
        refresh_token_repository: RefreshTokenRepository,
        permission_service: RbacPermissionService,
        unit_of_work: UnitOfWork,
        secret_key: str,
        algorithm: str,
        access_token_expire_minutes: int,
        refresh_token_expire_days: int,
    ) -> None:
        self._users = user_repository
        self._sessions = user_session_repository
        self._refresh_tokens = refresh_token_repository
        self._permission_service = permission_service
        self._uow = unit_of_work
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._access_ttl = timedelta(minutes=access_token_expire_minutes)
        self._refresh_ttl = timedelta(days=refresh_token_expire_days)

    async def execute(self, input_dto: AuthenticateUserInput) -> AuthenticateUserOutput:
        now = datetime.now(UTC)
        user = await self._users.get_by_email_any_organization(EmailAddress(input_dto.email))
        if user is None:
            raise InvalidCredentialsError()

        # Password verification comes *before* the lock/status checks below
        # — checking lock status first would leak whether a given email's
        # account happens to be locked to a caller who has not yet proven
        # they hold the password (see `InvalidCredentialsError`'s own
        # anti-enumeration docstring). A wrong password against an
        # already-locked account still raises the same generic error, not
        # `AccountLockedError`.
        if not verify_password(input_dto.password, user.password_hash.value):
            user.record_login_failure(now=now)
            await self._users.add(user)
            self._uow.collect_events(user.pull_events())
            await self._uow.commit()
            raise InvalidCredentialsError()

        if user.is_locked(now=now):
            raise AccountLockedError(user.id)

        if user.status is not UserStatus.ACTIVE:
            raise InactiveAccountError(user.id, user.status.value)

        user.record_login_success(now=now)
        await self._users.add(user)

        session = UserSession.start(
            organization_id=user.organization_id,
            user_id=user.id,
            expires_at=now + self._refresh_ttl,
            now=now,
        )
        await self._sessions.add(session)
        # `RefreshToken.user_session_id` is a real FK to `user_sessions.id`,
        # but the two ORM models have no declared `relationship()` between
        # them (this codebase's repositories stay flat — see
        # `infrastructure/repositories.py`'s own module docstring), so
        # SQLAlchemy's flush has no dependency graph to sort by and can
        # attempt the `refresh_tokens` insert before the `user_sessions`
        # one that must precede it, tripping the FK constraint. An
        # explicit flush here forces the session row to exist first —
        # confirmed necessary by an actual `ForeignKeyViolationError`
        # against real PostgreSQL, not a hypothetical.
        await self._uow.flush()

        raw_refresh_token = generate_raw_refresh_token()
        refresh_token = RefreshToken.issue(
            organization_id=user.organization_id,
            user_session_id=session.id,
            token_hash=hash_refresh_token(raw_refresh_token),
            expires_at=now + self._refresh_ttl,
            now=now,
        )
        await self._refresh_tokens.add(refresh_token)

        access_token = encode_token(
            subject=str(user.id),
            organization_id=str(user.organization_id),
            token_type=TokenType.ACCESS,
            expires_delta=self._access_ttl,
            secret_key=self._secret_key,
            algorithm=self._algorithm,
            session_id=str(session.id),
        )

        permissions = await self._permission_service.get_effective_permission_codes(user.id)

        events = user.pull_events()
        events.extend(session.pull_events())
        events.extend(refresh_token.pull_events())
        self._uow.collect_events(events)
        await self._uow.commit()

        return AuthenticateUserOutput(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            principal=AuthenticatedPrincipalDTO(
                user_id=user.id,
                organization_id=user.organization_id,
                session_id=session.id,
                email=str(user.email),
                permissions=permissions,
            ),
        )
