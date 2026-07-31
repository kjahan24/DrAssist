"""Integration tests for `SqlAlchemyDepartmentRepository`, including the FK
to `organizations`, against a real PostgreSQL instance."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organization.domain.entities import Department, Organization
from app.modules.organization.domain.enums import DepartmentStatus, OrganizationType
from app.modules.organization.domain.value_objects import OrganizationCode
from app.modules.organization.infrastructure.repositories import (
    SqlAlchemyDepartmentRepository,
    SqlAlchemyOrganizationRepository,
)


def _unique_code() -> str:
    return f"ORG-{uuid4().hex[:12].upper()}"


async def _persist_organization(db_session: AsyncSession) -> Organization:
    org_repo = SqlAlchemyOrganizationRepository(db_session)
    organization = Organization.create(
        organization_code=OrganizationCode(_unique_code()),
        name="Department Test Org",
        type=OrganizationType.CLINIC,
    )
    await org_repo.add(organization)
    await db_session.commit()
    return organization


class TestDepartmentRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization = await _persist_organization(db_session)
        repo = SqlAlchemyDepartmentRepository(db_session)

        department = Department.create(
            organization_id=organization.id, name="Cardiology", description="Heart care"
        )
        await repo.add(department)
        await db_session.commit()

        reloaded = await repo.get_by_id(department.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.name == "Cardiology"
        assert reloaded.description == "Heart care"
        assert reloaded.status is DepartmentStatus.ACTIVE

    async def test_list_by_organization_scopes_to_a_single_organization(
        self, db_session: AsyncSession
    ) -> None:
        org_a = await _persist_organization(db_session)
        org_b = await _persist_organization(db_session)
        repo = SqlAlchemyDepartmentRepository(db_session)

        dept_a = Department.create(organization_id=org_a.id, name="Radiology")
        dept_b = Department.create(organization_id=org_b.id, name="Oncology")
        await repo.add(dept_a)
        await repo.add(dept_b)
        await db_session.commit()

        departments_for_a = await repo.list_by_organization(org_a.id)
        assert [d.id for d in departments_for_a] == [dept_a.id]

    async def test_status_change_persists(self, db_session: AsyncSession) -> None:
        organization = await _persist_organization(db_session)
        repo = SqlAlchemyDepartmentRepository(db_session)

        department = Department.create(organization_id=organization.id, name="Neurology")
        await repo.add(department)
        await db_session.commit()

        department.deactivate()
        await repo.add(department)
        await db_session.commit()

        reloaded = await repo.get_by_id(department.id)
        assert reloaded is not None
        assert reloaded.status is DepartmentStatus.INACTIVE


class TestDepartmentSearch:
    """Search & Filtering module — `SqlAlchemyDepartmentRepository.search`."""

    async def test_scopes_to_organization_and_matches_query(self, db_session: AsyncSession) -> None:
        org_a = await _persist_organization(db_session)
        org_b = await _persist_organization(db_session)
        repo = SqlAlchemyDepartmentRepository(db_session)
        cardiology = Department.create(organization_id=org_a.id, name="Cardiology")
        oncology_other_org = Department.create(organization_id=org_b.id, name="Cardiology Annex")
        await repo.add(cardiology)
        await repo.add(oncology_other_org)
        await db_session.commit()

        results, total = await repo.search(organization_id=org_a.id, query="cardio")

        assert total == 1
        assert [d.id for d in results] == [cardiology.id]

    async def test_status_filter_and_pagination(self, db_session: AsyncSession) -> None:
        organization = await _persist_organization(db_session)
        repo = SqlAlchemyDepartmentRepository(db_session)
        active_one = Department.create(organization_id=organization.id, name="Active One")
        active_two = Department.create(organization_id=organization.id, name="Active Two")
        inactive = Department.create(organization_id=organization.id, name="Inactive Dept")
        inactive.deactivate()
        for dept in (active_one, active_two, inactive):
            await repo.add(dept)
        await db_session.commit()

        results, total = await repo.search(
            organization_id=organization.id,
            statuses=[DepartmentStatus.ACTIVE],
            sort_by="name",
            sort_order="asc",
            limit=1,
        )

        assert total == 2
        assert [d.id for d in results] == [active_one.id]


class TestDepartmentRequiresValidOrganization:
    async def test_nonexistent_organization_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyDepartmentRepository(db_session)
        department = Department.create(organization_id=uuid4(), name="Orphan Department")
        await repo.add(department)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
