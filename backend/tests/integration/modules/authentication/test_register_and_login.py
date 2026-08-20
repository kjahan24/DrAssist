"""Integration tests for the full `RegisterUser` -> `AuthenticateUser`
flow against a real PostgreSQL instance, using the exact same concrete
repositories/`UnitOfWork` wiring `api/dependencies.py` uses in production
(including the real `OrganizationFacade`, not a fake) — this is what
first caught a real `ForeignKeyViolationError` on `refresh_tokens
.user_session_id` (see `application/use_cases/authenticate_user.py`'s own
comment on the fix): `UserSession`/`RefreshToken` have no declared ORM
`relationship()` between them, so SQLAlchemy's flush had no dependency
graph to order the two inserts by, and the in-memory fakes the unit tests
use can't reproduce a real foreign-key constraint at all. This suite is
exactly the "PostgreSQL integration tests where applicable" this task's
own verification checklist calls for.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.authentication._helpers import unique_suffix

from app.core.container import get_event_bus
from app.core.security.jwt import TokenType, decode_token
from app.modules.authentication.application.dto import AuthenticateUserInput, RegisterUserInput
from app.modules.authentication.application.services.permission_service import (
    RbacPermissionService,
)
from app.modules.authentication.application.use_cases.authenticate_user import AuthenticateUser
from app.modules.authentication.application.use_cases.register_user import RegisterUser
from app.modules.authentication.domain.exceptions import (
    DuplicateEmailError,
    InvalidCredentialsError,
)
from app.modules.authentication.infrastructure.repositories import (
    SqlAlchemyPermissionRepository,
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemyRoleRepository,
    SqlAlchemyUserRepository,
    SqlAlchemyUserSessionRepository,
)
from app.modules.organization.container import build_organization_facade
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork

_SECRET_KEY = "integration-test-secret-key"
_ALGORITHM = "HS256"


def _register_use_case(session: AsyncSession) -> RegisterUser:
    return RegisterUser(
        user_repository=SqlAlchemyUserRepository(session),
        organization_provisioning_port=build_organization_facade(session),
        unit_of_work=SqlAlchemyUnitOfWork(session, event_bus=get_event_bus()),
    )


def _login_use_case(session: AsyncSession) -> AuthenticateUser:
    role_repository = SqlAlchemyRoleRepository(session)
    permission_repository = SqlAlchemyPermissionRepository(session)
    return AuthenticateUser(
        user_repository=SqlAlchemyUserRepository(session),
        user_session_repository=SqlAlchemyUserSessionRepository(session),
        refresh_token_repository=SqlAlchemyRefreshTokenRepository(session),
        permission_service=RbacPermissionService(
            role_repository=role_repository, permission_repository=permission_repository
        ),
        unit_of_work=SqlAlchemyUnitOfWork(session, event_bus=get_event_bus()),
        secret_key=_SECRET_KEY,
        algorithm=_ALGORITHM,
        access_token_expire_minutes=30,
        refresh_token_expire_days=7,
    )


class TestRegisterThenLogin:
    async def test_a_newly_registered_user_can_immediately_log_in(
        self, db_session: AsyncSession
    ) -> None:
        email = f"e2e-{unique_suffix()}@example.com"

        register_output = await _register_use_case(db_session).execute(
            RegisterUserInput(
                email=email, password="StrongPass1", first_name="Ada", last_name="Lovelace"
            )
        )

        login_output = await _login_use_case(db_session).execute(
            AuthenticateUserInput(email=email, password="StrongPass1")
        )

        assert login_output.principal.user_id == register_output.user_id
        assert login_output.principal.organization_id == register_output.organization_id
        assert login_output.access_token
        assert login_output.refresh_token

        claims = decode_token(
            login_output.access_token,
            secret_key=_SECRET_KEY,
            algorithm=_ALGORITHM,
            expected_type=TokenType.ACCESS,
        )
        assert claims.subject == str(register_output.user_id)
        assert claims.session_id == str(login_output.principal.session_id)

    async def test_login_fails_with_the_wrong_password(self, db_session: AsyncSession) -> None:
        email = f"e2e-wrong-pw-{unique_suffix()}@example.com"
        await _register_use_case(db_session).execute(
            RegisterUserInput(
                email=email, password="StrongPass1", first_name="Ada", last_name="Lovelace"
            )
        )

        with pytest.raises(InvalidCredentialsError):
            await _login_use_case(db_session).execute(
                AuthenticateUserInput(email=email, password="WrongPassword1")
            )

    async def test_register_provisions_a_real_queryable_organization(
        self, db_session: AsyncSession
    ) -> None:
        email = f"e2e-org-{unique_suffix()}@example.com"

        output = await _register_use_case(db_session).execute(
            RegisterUserInput(
                email=email, password="StrongPass1", first_name="Grace", last_name="Hopper"
            )
        )

        facade = build_organization_facade(db_session)
        assert await facade.organization_exists(output.organization_id) is True
        summary = await facade.get_organization_summary(output.organization_id)
        assert summary is not None
        assert "Grace Hopper" in summary.name

    async def test_registering_the_same_email_twice_fails_on_the_second_attempt(
        self, db_session: AsyncSession
    ) -> None:
        email = f"e2e-dupe-{unique_suffix()}@example.com"
        await _register_use_case(db_session).execute(
            RegisterUserInput(
                email=email, password="StrongPass1", first_name="Ada", last_name="Lovelace"
            )
        )

        with pytest.raises(DuplicateEmailError):
            await _register_use_case(db_session).execute(
                RegisterUserInput(
                    email=email, password="AnotherPass1", first_name="Ada", last_name="Impersonator"
                )
            )
