"""Unit tests for `ValidateAccessToken` — the logic behind the
`get_current_user` authorization dependency. Uses real JWT encode/decode
(fast, pure) against fake repositories."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.core.security.jwt import TokenType, encode_token
from app.modules.authentication.application.exceptions import AuthenticationError
from app.modules.authentication.application.services.permission_service import (
    RbacPermissionService,
)
from app.modules.authentication.application.services.token_validation_service import (
    ValidateAccessToken,
    ValidateAccessTokenInput,
)
from app.modules.authentication.domain.entities import Permission, Role, User, UserSession
from app.modules.authentication.domain.enums import UserStatus
from app.modules.authentication.domain.value_objects import HashedPassword, PermissionCode
from app.shared.domain.common_value_objects import EmailAddress
from tests.unit.modules.authentication.application.fakes import (
    FakePermissionRepository,
    FakeRoleRepository,
    FakeUserRepository,
    FakeUserSessionRepository,
)

SECRET_KEY = "unit-test-secret-key"
ALGORITHM = "HS256"
VALID_HASH = "$2b$12$" + "a" * 53


@pytest.fixture
def user_repository() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture
def session_repository() -> FakeUserSessionRepository:
    return FakeUserSessionRepository()


@pytest.fixture
def role_repository() -> FakeRoleRepository:
    return FakeRoleRepository()


@pytest.fixture
def permission_repository() -> FakePermissionRepository:
    return FakePermissionRepository()


@pytest.fixture
def use_case(
    user_repository: FakeUserRepository,
    session_repository: FakeUserSessionRepository,
    role_repository: FakeRoleRepository,
    permission_repository: FakePermissionRepository,
) -> ValidateAccessToken:
    permission_service = RbacPermissionService(
        role_repository=role_repository, permission_repository=permission_repository
    )
    return ValidateAccessToken(
        user_repository=user_repository,
        user_session_repository=session_repository,
        permission_service=permission_service,
        secret_key=SECRET_KEY,
        algorithm=ALGORITHM,
    )


async def _active_user_with_session(
    user_repository: FakeUserRepository, session_repository: FakeUserSessionRepository
) -> tuple[User, UserSession]:
    now = datetime.now(UTC)
    user = User.register(
        organization_id=uuid4(),
        email=EmailAddress("doctor@example.com"),
        password_hash=HashedPassword(VALID_HASH),
        first_name="Ada",
        last_name="Lovelace",
    )
    user.activate()
    await user_repository.add(user)

    session = UserSession.start(
        organization_id=user.organization_id,
        user_id=user.id,
        expires_at=now + timedelta(days=1),
        now=now,
    )
    await session_repository.add(session)
    return user, session


def _access_token_for(user: User, session: UserSession) -> str:
    return encode_token(
        subject=str(user.id),
        organization_id=str(user.organization_id),
        token_type=TokenType.ACCESS,
        expires_delta=timedelta(minutes=30),
        secret_key=SECRET_KEY,
        algorithm=ALGORITHM,
        session_id=str(session.id),
    )


class TestValidateAccessToken:
    async def test_valid_token_resolves_to_the_authenticated_principal(
        self,
        use_case: ValidateAccessToken,
        user_repository: FakeUserRepository,
        session_repository: FakeUserSessionRepository,
    ) -> None:
        user, session = await _active_user_with_session(user_repository, session_repository)
        token = _access_token_for(user, session)

        principal = await use_case.execute(ValidateAccessTokenInput(raw_token=token))

        assert principal.user_id == user.id
        assert principal.organization_id == user.organization_id
        assert principal.session_id == session.id
        assert principal.email == "doctor@example.com"

    async def test_includes_effective_permissions(
        self,
        use_case: ValidateAccessToken,
        user_repository: FakeUserRepository,
        session_repository: FakeUserSessionRepository,
        role_repository: FakeRoleRepository,
        permission_repository: FakePermissionRepository,
    ) -> None:
        user, session = await _active_user_with_session(user_repository, session_repository)
        role = Role.create(organization_id=user.organization_id, name="Doctor")
        await role_repository.add(role)
        await role_repository.assign_to_user(
            organization_id=user.organization_id,
            user_id=user.id,
            role_id=role.id,
            granted_by=None,
            granted_at=datetime.now(UTC),
        )
        permission = Permission.create(
            code=PermissionCode("patients.read"), module="patients", description="Read"
        )
        await permission_repository.add(permission)
        permission_repository.seed_role_permission(role.id, permission.id)

        principal = await use_case.execute(
            ValidateAccessTokenInput(raw_token=_access_token_for(user, session))
        )

        assert principal.permissions == frozenset({"patients.read"})

    async def test_garbage_token_raises_authentication_error(
        self, use_case: ValidateAccessToken
    ) -> None:
        with pytest.raises(AuthenticationError):
            await use_case.execute(ValidateAccessTokenInput(raw_token="not-a-jwt"))

    async def test_expired_token_raises_authentication_error(
        self,
        use_case: ValidateAccessToken,
        user_repository: FakeUserRepository,
        session_repository: FakeUserSessionRepository,
    ) -> None:
        user, session = await _active_user_with_session(user_repository, session_repository)
        expired_token = encode_token(
            subject=str(user.id),
            organization_id=str(user.organization_id),
            token_type=TokenType.ACCESS,
            expires_delta=timedelta(seconds=-1),
            secret_key=SECRET_KEY,
            algorithm=ALGORITHM,
            session_id=str(session.id),
        )

        with pytest.raises(AuthenticationError):
            await use_case.execute(ValidateAccessTokenInput(raw_token=expired_token))

    async def test_refresh_token_is_rejected_for_access_purposes(
        self,
        use_case: ValidateAccessToken,
        user_repository: FakeUserRepository,
        session_repository: FakeUserSessionRepository,
    ) -> None:
        user, session = await _active_user_with_session(user_repository, session_repository)
        refresh_token = encode_token(
            subject=str(user.id),
            organization_id=str(user.organization_id),
            token_type=TokenType.REFRESH,
            expires_delta=timedelta(days=7),
            secret_key=SECRET_KEY,
            algorithm=ALGORITHM,
            session_id=str(session.id),
        )

        with pytest.raises(AuthenticationError):
            await use_case.execute(ValidateAccessTokenInput(raw_token=refresh_token))

    async def test_unknown_user_raises_authentication_error(
        self, use_case: ValidateAccessToken
    ) -> None:
        token = encode_token(
            subject=str(uuid4()),
            organization_id=str(uuid4()),
            token_type=TokenType.ACCESS,
            expires_delta=timedelta(minutes=30),
            secret_key=SECRET_KEY,
            algorithm=ALGORITHM,
            session_id=str(uuid4()),
        )
        with pytest.raises(AuthenticationError):
            await use_case.execute(ValidateAccessTokenInput(raw_token=token))

    async def test_inactive_user_status_raises_authentication_error(
        self,
        use_case: ValidateAccessToken,
        user_repository: FakeUserRepository,
        session_repository: FakeUserSessionRepository,
    ) -> None:
        now = datetime.now(UTC)
        user = User.register(
            organization_id=uuid4(),
            email=EmailAddress("still.invited@example.com"),
            password_hash=HashedPassword(VALID_HASH),
            first_name="Not",
            last_name="Active",
        )
        assert user.status is UserStatus.INVITED  # never activated
        await user_repository.add(user)
        session = UserSession.start(
            organization_id=user.organization_id,
            user_id=user.id,
            expires_at=now + timedelta(days=1),
            now=now,
        )
        await session_repository.add(session)

        with pytest.raises(AuthenticationError):
            await use_case.execute(
                ValidateAccessTokenInput(raw_token=_access_token_for(user, session))
            )

    async def test_revoked_session_raises_authentication_error(
        self,
        use_case: ValidateAccessToken,
        user_repository: FakeUserRepository,
        session_repository: FakeUserSessionRepository,
    ) -> None:
        user, session = await _active_user_with_session(user_repository, session_repository)
        session.revoke(reason="logout", now=datetime.now(UTC))
        await session_repository.add(session)

        with pytest.raises(AuthenticationError):
            await use_case.execute(
                ValidateAccessTokenInput(raw_token=_access_token_for(user, session))
            )

    async def test_token_missing_session_claim_raises_authentication_error(
        self,
        use_case: ValidateAccessToken,
        user_repository: FakeUserRepository,
        session_repository: FakeUserSessionRepository,
    ) -> None:
        user, _ = await _active_user_with_session(user_repository, session_repository)
        token_without_session = encode_token(
            subject=str(user.id),
            organization_id=str(user.organization_id),
            token_type=TokenType.ACCESS,
            expires_delta=timedelta(minutes=30),
            secret_key=SECRET_KEY,
            algorithm=ALGORITHM,
        )

        with pytest.raises(AuthenticationError):
            await use_case.execute(ValidateAccessTokenInput(raw_token=token_without_session))
