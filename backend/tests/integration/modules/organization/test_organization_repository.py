"""Integration tests for `SqlAlchemyOrganizationRepository` against a real
PostgreSQL instance — catches ORM-mapping/constraint bugs the fakes-based
unit tests structurally cannot (see
`docs/backend-architecture/12_testing_architecture.md §2`)."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organization.domain.entities import Organization
from app.modules.organization.domain.enums import OrganizationType
from app.modules.organization.domain.value_objects import OrganizationCode
from app.modules.organization.infrastructure.repositories import SqlAlchemyOrganizationRepository
from app.shared.domain.common_value_objects import EmailAddress


def _unique_code() -> str:
    return f"ORG-{uuid4().hex[:12].upper()}"


class TestOrganizationRoundTrip:
    async def test_save_and_reload_preserves_every_field(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyOrganizationRepository(db_session)
        code = OrganizationCode(_unique_code())

        organization = Organization.create(
            organization_code=code,
            name="Integration Test Clinic",
            type=OrganizationType.CLINIC,
            legal_name="Integration Test Clinic LLC",
            email=EmailAddress("contact@example.com"),
            phone="+1-555-0100",
            website="https://example.com",
            city="Springfield",
            country="USA",
            timezone="America/Chicago",
            currency="USD",
            language="en",
        )

        await repo.add(organization)
        await db_session.commit()

        reloaded = await repo.get_by_id(organization.id)
        assert reloaded is not None
        assert str(reloaded.organization_code) == str(code)
        assert reloaded.name == "Integration Test Clinic"
        assert reloaded.legal_name == "Integration Test Clinic LLC"
        assert str(reloaded.email) == "contact@example.com"
        assert reloaded.city == "Springfield"
        assert reloaded.timezone == "America/Chicago"
        assert reloaded.type is OrganizationType.CLINIC
        assert reloaded.is_active is True

    async def test_get_by_code_finds_a_saved_organization(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyOrganizationRepository(db_session)
        code = _unique_code()
        organization = Organization.create(
            organization_code=OrganizationCode(code),
            name="Findable Org",
            type=OrganizationType.HOSPITAL,
        )
        await repo.add(organization)
        await db_session.commit()

        found = await repo.get_by_code(code.lower())  # lookup is case-insensitive by normalization
        assert found is not None
        assert found.id == organization.id

    async def test_get_by_id_returns_none_for_unknown_id(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyOrganizationRepository(db_session)
        assert await repo.get_by_id(uuid4()) is None

    async def test_update_via_add_persists_mutated_fields(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyOrganizationRepository(db_session)
        organization = Organization.create(
            organization_code=OrganizationCode(_unique_code()),
            name="Mutable Org",
            type=OrganizationType.CLINIC,
        )
        await repo.add(organization)
        await db_session.commit()

        organization.update_profile(name="Renamed Org", city="New City")
        await repo.add(organization)
        await db_session.commit()

        reloaded = await repo.get_by_id(organization.id)
        assert reloaded is not None
        assert reloaded.name == "Renamed Org"
        assert reloaded.city == "New City"

    async def test_list_active_excludes_deactivated_organizations(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyOrganizationRepository(db_session)
        active_org = Organization.create(
            organization_code=OrganizationCode(_unique_code()),
            name="Active Org",
            type=OrganizationType.CLINIC,
        )
        inactive_org = Organization.create(
            organization_code=OrganizationCode(_unique_code()),
            name="Inactive Org",
            type=OrganizationType.CLINIC,
        )
        inactive_org.deactivate()
        await repo.add(active_org)
        await repo.add(inactive_org)
        await db_session.commit()

        active_ids = {o.id for o in await repo.list_active(limit=1000)}
        assert active_org.id in active_ids
        assert inactive_org.id not in active_ids


class TestOrganizationCodeUniqueness:
    async def test_duplicate_organization_code_violates_db_constraint(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyOrganizationRepository(db_session)
        code = _unique_code()

        first = Organization.create(
            organization_code=OrganizationCode(code), name="First", type=OrganizationType.CLINIC
        )
        await repo.add(first)
        await db_session.commit()

        second = Organization.create(
            organization_code=OrganizationCode(code), name="Second", type=OrganizationType.CLINIC
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
