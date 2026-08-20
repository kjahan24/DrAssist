"""Integration tests for `SqlAlchemyUserRepository`, including
`get_by_email_any_organization` and the `uq_users_email_global` partial
unique index that backs it as a real database constraint (added by this
task alongside self-service registration/login) — against a real
PostgreSQL instance.

Every email below is suffixed with `unique_suffix()` — this suite runs
against a real, persistent database with no per-test rollback, and
`uq_users_email_global` is *globally* unique (not scoped to a test or
organization), so a bare literal would collide across test runs exactly
like `tests.integration.modules.authentication.test_role_repository`'s
own docstring already explains for `uq_roles_system_name`.
"""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.authentication._helpers import unique_suffix

from app.modules.authentication.domain.entities import User
from app.modules.authentication.domain.value_objects import HashedPassword
from app.modules.authentication.infrastructure.repositories import SqlAlchemyUserRepository
from app.shared.domain.common_value_objects import EmailAddress

_PASSWORD_HASH = HashedPassword("$2b$12$" + "a" * 53)


class TestGetByEmailAnyOrganization:
    async def test_finds_a_user_without_knowing_their_organization(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        email = EmailAddress(f"global-lookup-{unique_suffix()}@example.com")
        user = User.register(
            organization_id=uuid4(),
            email=email,
            password_hash=_PASSWORD_HASH,
            first_name="Global",
            last_name="Lookup",
        )
        await repo.add(user)
        await db_session.commit()

        found = await repo.get_by_email_any_organization(email)
        assert found is not None
        assert found.id == user.id
        assert found.organization_id == user.organization_id

    async def test_returns_none_for_an_unregistered_email(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        result = await repo.get_by_email_any_organization(
            EmailAddress(f"never-registered-{unique_suffix()}@example.com")
        )
        assert result is None

    async def test_is_case_insensitive(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        suffix = unique_suffix()
        user = User.register(
            organization_id=uuid4(),
            email=EmailAddress(f"MixedCase-{suffix}@Example.com"),
            password_hash=_PASSWORD_HASH,
            first_name="Mixed",
            last_name="Case",
        )
        await repo.add(user)
        await db_session.commit()

        found = await repo.get_by_email_any_organization(
            EmailAddress(f"mixedcase-{suffix}@example.com")
        )
        assert found is not None
        assert found.id == user.id


class TestGlobalEmailUniqueness:
    async def test_a_second_user_with_the_same_email_in_a_different_organization_violates_the_index(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        email = EmailAddress(f"dupe-{unique_suffix()}@example.com")

        first = User.register(
            organization_id=uuid4(),
            email=email,
            password_hash=_PASSWORD_HASH,
            first_name="First",
            last_name="User",
        )
        await repo.add(first)
        await db_session.commit()

        second = User.register(
            organization_id=uuid4(),  # a different tenant
            email=email,
            password_hash=_PASSWORD_HASH,
            first_name="Second",
            last_name="User",
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
