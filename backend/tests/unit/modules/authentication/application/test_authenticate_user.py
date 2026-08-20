"""Unit tests for `AuthenticateUser`, using in-memory fakes and real (fast,
pure) JWT encode/decode."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.core.security.jwt import TokenType, decode_token
from app.core.security.password_hashing import hash_password
from app.core.security.token_hashing import hash_refresh_token
from app.modules.authentication.application.dto import AuthenticateUserInput
from app.modules.authentication.application.services.permission_service import (
    RbacPermissionService,
)
from app.modules.authentication.application.use_cases.authenticate_user import AuthenticateUser
from app.modules.authentication.domain.entities import Permission, Role, User
from app.modules.authentication.domain.enums import UserStatus
from app.modules.authentication.domain.exceptions import (
    AccountLockedError,
    InactiveAccountError,
    InvalidCredentialsError,
)
from app.modules.authentication.domain.value_objects import HashedPassword, PermissionCode
from app.shared.domain.common_value_objects import EmailAddress
from tests.unit.modules.authentication.application.fakes import (
    FakePermissionRepository,
    FakeRefreshTokenRepository,
    FakeRoleRepository,
    FakeUnitOfWork,
    FakeUserRepository,
    FakeUserSessionRepository,
)

SECRET_KEY = "unit-test-secret-key"
ALGORITHM = "HS256"
_PASSWORD = "CorrectHorse1"


def _seeded() -> (
    tuple[
        AuthenticateUser,
        FakeUserRepository,
        FakeUserSessionRepository,
        FakeRefreshTokenRepository,
        FakeRoleRepository,
        FakePermissionRepository,
        FakeUnitOfWork,
    ]
):
    users = FakeUserRepository()
    sessions = FakeUserSessionRepository()
    refresh_tokens = FakeRefreshTokenRepository()
    roles = FakeRoleRepository()
    permissions = FakePermissionRepository()
    uow = FakeUnitOfWork()
    permission_service = RbacPermissionService(
        role_repository=roles, permission_repository=permissions
    )
    use_case = AuthenticateUser(
        user_repository=users,
        user_session_repository=sessions,
        refresh_token_repository=refresh_tokens,
        permission_service=permission_service,
        unit_of_work=uow,
        secret_key=SECRET_KEY,
        algorithm=ALGORITHM,
        access_token_expire_minutes=30,
        refresh_token_expire_days=7,
    )
    return use_case, users, sessions, refresh_tokens, roles, permissions, uow


async def _active_user(users: FakeUserRepository, **overrides: object) -> User:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "email": EmailAddress("doctor@example.com"),
        "password_hash": HashedPassword(hash_password(_PASSWORD)),
        "first_name": "Ada",
        "last_name": "Lovelace",
    }
    defaults.update(overrides)
    user = User.register(**defaults)  # type: ignore[arg-type]
    user.activate()
    await users.add(user)
    return user


class TestAuthenticateUser:
    async def test_successful_login_returns_tokens_and_principal(self) -> None:
        use_case, users, sessions, refresh_tokens, *_ = _seeded()
        user = await _active_user(users)

        output = await use_case.execute(
            AuthenticateUserInput(email="doctor@example.com", password=_PASSWORD)
        )

        assert output.principal.user_id == user.id
        assert output.principal.organization_id == user.organization_id
        assert output.principal.email == "doctor@example.com"

        claims = decode_token(
            output.access_token,
            secret_key=SECRET_KEY,
            algorithm=ALGORITHM,
            expected_type=TokenType.ACCESS,
        )
        assert claims.subject == str(user.id)
        assert claims.session_id == str(output.principal.session_id)

        active_sessions = await sessions.list_active_for_user(user.id)
        assert len(active_sessions) == 1
        assert active_sessions[0].id == output.principal.session_id

        active_refresh = await refresh_tokens.list_active_for_session(output.principal.session_id)
        assert len(active_refresh) == 1
        assert active_refresh[0].token_hash == hash_refresh_token(output.refresh_token)

    async def test_records_login_success_on_the_user(self) -> None:
        use_case, users, *_ = _seeded()
        user = await _active_user(users)

        await use_case.execute(
            AuthenticateUserInput(email="doctor@example.com", password=_PASSWORD)
        )

        reloaded = await users.get_by_id(user.id)
        assert reloaded is not None
        assert reloaded.failed_login_attempts == 0
        assert reloaded.last_login_at is not None

    async def test_includes_effective_permissions(self) -> None:
        use_case, users, _, _, roles, permissions, _ = _seeded()
        user = await _active_user(users)
        role = Role.create(organization_id=user.organization_id, name="Doctor")
        await roles.add(role)
        await roles.assign_to_user(
            organization_id=user.organization_id,
            user_id=user.id,
            role_id=role.id,
            granted_by=None,
            granted_at=datetime.now(UTC),
        )
        permission = Permission.create(code=PermissionCode("patients.read"), name="Read patients")
        await permissions.add(permission)
        permissions.seed_role_permission(role.id, permission.id)

        output = await use_case.execute(
            AuthenticateUserInput(email="doctor@example.com", password=_PASSWORD)
        )

        assert output.principal.permissions == frozenset({"patients.read"})

    async def test_unknown_email_raises_invalid_credentials(self) -> None:
        use_case, *_ = _seeded()

        with pytest.raises(InvalidCredentialsError):
            await use_case.execute(
                AuthenticateUserInput(email="ghost@example.com", password=_PASSWORD)
            )

    async def test_wrong_password_raises_invalid_credentials_and_records_failure(self) -> None:
        use_case, users, *_ = _seeded()
        user = await _active_user(users)

        with pytest.raises(InvalidCredentialsError):
            await use_case.execute(
                AuthenticateUserInput(email="doctor@example.com", password="WrongPassword1")
            )

        reloaded = await users.get_by_id(user.id)
        assert reloaded is not None
        assert reloaded.failed_login_attempts == 1

    async def test_wrong_password_never_reveals_account_lock_status(self) -> None:
        """A *wrong* password against an already-locked account still
        raises the same generic `InvalidCredentialsError`, never
        `AccountLockedError` — a caller who hasn't proven they hold the
        password must never learn the account is locked. See
        `InvalidCredentialsError`'s own anti-enumeration docstring."""
        use_case, users, *_ = _seeded()
        user = await _active_user(users)
        user.locked_until = datetime.now(UTC) + timedelta(minutes=15)
        await users.add(user)

        with pytest.raises(InvalidCredentialsError):
            await use_case.execute(
                AuthenticateUserInput(email="doctor@example.com", password="WrongPassword1")
            )

    async def test_locked_account_raises_account_locked_even_with_correct_password(self) -> None:
        use_case, users, *_ = _seeded()
        user = await _active_user(users)
        user.locked_until = datetime.now(UTC) + timedelta(minutes=15)
        await users.add(user)

        with pytest.raises(AccountLockedError):
            await use_case.execute(
                AuthenticateUserInput(email="doctor@example.com", password=_PASSWORD)
            )

    async def test_inactive_account_raises_after_correct_password(self) -> None:
        use_case, users, *_ = _seeded()
        user = User.register(
            organization_id=uuid4(),
            email=EmailAddress("invited@example.com"),
            password_hash=HashedPassword(hash_password(_PASSWORD)),
            first_name="Not",
            last_name="Active",
        )
        assert user.status is UserStatus.INVITED  # never activated
        await users.add(user)

        with pytest.raises(InactiveAccountError):
            await use_case.execute(
                AuthenticateUserInput(email="invited@example.com", password=_PASSWORD)
            )

    async def test_five_consecutive_failures_lock_the_account(self) -> None:
        use_case, users, *_ = _seeded()
        await _active_user(users)

        for _ in range(5):
            with pytest.raises(InvalidCredentialsError):
                await use_case.execute(
                    AuthenticateUserInput(email="doctor@example.com", password="WrongPassword1")
                )

        with pytest.raises(AccountLockedError):
            await use_case.execute(
                AuthenticateUserInput(email="doctor@example.com", password=_PASSWORD)
            )
