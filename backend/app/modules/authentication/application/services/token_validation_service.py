"""`ValidateAccessToken` — verifies an already-issued access token and
resolves it to an `AuthenticatedPrincipalDTO`.

This is the backing logic for the `get_current_user` authorization
dependency (`app/api/deps.py`) — it is explicitly **not** the login flow:
it never checks a password, it only validates a token someone already
holds and confirms the user/session behind it are still valid. That
distinction is what makes it in-scope foundation work even though
login/register are excluded from this task.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.core.logging import get_logger
from app.core.security.jwt import InvalidTokenError, TokenType, decode_token
from app.modules.authentication.application.dto import AuthenticatedPrincipalDTO
from app.modules.authentication.application.exceptions import AuthenticationError
from app.modules.authentication.application.services.permission_service import (
    RbacPermissionService,
)
from app.modules.authentication.domain.repositories import UserRepository, UserSessionRepository
from app.shared.application.use_case import UseCase

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ValidateAccessTokenInput:
    raw_token: str


class ValidateAccessToken(UseCase[ValidateAccessTokenInput, AuthenticatedPrincipalDTO]):
    def __init__(
        self,
        *,
        user_repository: UserRepository,
        user_session_repository: UserSessionRepository,
        permission_service: RbacPermissionService,
        secret_key: str,
        algorithm: str,
    ) -> None:
        self._users = user_repository
        self._sessions = user_session_repository
        self._permission_service = permission_service
        self._secret_key = secret_key
        self._algorithm = algorithm

    async def execute(self, input_dto: ValidateAccessTokenInput) -> AuthenticatedPrincipalDTO:
        try:
            claims = decode_token(
                input_dto.raw_token,
                secret_key=self._secret_key,
                algorithm=self._algorithm,
                expected_type=TokenType.ACCESS,
            )
        except InvalidTokenError as exc:
            logger.info("access_token_rejected", reason=str(exc))
            raise AuthenticationError("invalid or expired access token") from exc

        if claims.session_id is None:
            raise AuthenticationError("access token is missing its session claim")

        try:
            user_id = UUID(claims.subject)
            session_id = UUID(claims.session_id)
        except ValueError as exc:
            raise AuthenticationError("access token claims are malformed") from exc

        user = await self._users.get_by_id(user_id)
        now = datetime.now(UTC)
        if user is None or user.organization_id != UUID(claims.organization_id):
            raise AuthenticationError("token does not resolve to a known user")
        if not user.can_authenticate(now=now):
            raise AuthenticationError(f"user account is not usable (status={user.status.value})")

        session = await self._sessions.get_by_id(session_id)
        if session is None or session.user_id != user.id:
            raise AuthenticationError("token session is not known")
        if not session.is_active(now=now):
            raise AuthenticationError("token session has expired or been revoked")

        permissions = await self._permission_service.get_effective_permission_codes(user.id)

        return AuthenticatedPrincipalDTO(
            user_id=user.id,
            organization_id=user.organization_id,
            session_id=session.id,
            email=str(user.email),
            permissions=permissions,
        )
