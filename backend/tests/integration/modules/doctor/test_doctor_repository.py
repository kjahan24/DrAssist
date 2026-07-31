"""Integration tests for `SqlAlchemyDoctorRepository`, including the FKs to
`organizations`/`users`, against a real PostgreSQL instance."""

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.doctor._helpers import persist_organization, persist_user

from app.modules.doctor.domain.entities import Doctor
from app.modules.doctor.domain.enums import DoctorStatus
from app.modules.doctor.infrastructure.repositories import SqlAlchemyDoctorRepository


class TestDoctorRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        user = await persist_user(db_session, organization_id=organization.id)
        repo = SqlAlchemyDoctorRepository(db_session)

        doctor = Doctor.create(
            organization_id=organization.id,
            user_id=user.id,
            employee_id="EMP-001",
            joining_date=date(2026, 1, 1),
        )
        await repo.add(doctor)
        await db_session.commit()

        reloaded = await repo.get_by_id(doctor.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.user_id == user.id
        assert reloaded.employee_id == "EMP-001"
        assert reloaded.status is DoctorStatus.ACTIVE

    async def test_status_change_persists(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        user = await persist_user(db_session, organization_id=organization.id)
        repo = SqlAlchemyDoctorRepository(db_session)

        doctor = Doctor.create(
            organization_id=organization.id,
            user_id=user.id,
            employee_id="EMP-002",
            joining_date=date(2026, 1, 1),
        )
        await repo.add(doctor)
        await db_session.commit()

        doctor.suspend()
        await repo.add(doctor)
        await db_session.commit()

        reloaded = await repo.get_by_id(doctor.id)
        assert reloaded is not None
        assert reloaded.status is DoctorStatus.SUSPENDED


class TestDoctorLookups:
    async def test_get_by_user_id_finds_the_doctor(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        user = await persist_user(db_session, organization_id=organization.id)
        repo = SqlAlchemyDoctorRepository(db_session)

        doctor = Doctor.create(
            organization_id=organization.id,
            user_id=user.id,
            employee_id="EMP-003",
            joining_date=date(2026, 1, 1),
        )
        await repo.add(doctor)
        await db_session.commit()

        reloaded = await repo.get_by_user_id(user.id)
        assert reloaded is not None
        assert reloaded.id == doctor.id

    async def test_get_by_employee_id_scopes_to_organization(
        self, db_session: AsyncSession
    ) -> None:
        org_a = await persist_organization(db_session)
        org_b = await persist_organization(db_session)
        user_a = await persist_user(db_session, organization_id=org_a.id)
        user_b = await persist_user(db_session, organization_id=org_b.id)
        repo = SqlAlchemyDoctorRepository(db_session)

        doctor_a = Doctor.create(
            organization_id=org_a.id,
            user_id=user_a.id,
            employee_id="SHARED-CODE",
            joining_date=date(2026, 1, 1),
        )
        doctor_b = Doctor.create(
            organization_id=org_b.id,
            user_id=user_b.id,
            employee_id="SHARED-CODE",
            joining_date=date(2026, 1, 1),
        )
        await repo.add(doctor_a)
        await repo.add(doctor_b)
        await db_session.commit()

        found_in_a = await repo.get_by_employee_id(
            organization_id=org_a.id, employee_id="SHARED-CODE"
        )
        found_in_b = await repo.get_by_employee_id(
            organization_id=org_b.id, employee_id="SHARED-CODE"
        )
        assert found_in_a is not None and found_in_a.id == doctor_a.id
        assert found_in_b is not None and found_in_b.id == doctor_b.id

    async def test_list_by_organization_scopes_to_a_single_organization(
        self, db_session: AsyncSession
    ) -> None:
        org_a = await persist_organization(db_session)
        org_b = await persist_organization(db_session)
        user_a = await persist_user(db_session, organization_id=org_a.id)
        user_b = await persist_user(db_session, organization_id=org_b.id)
        repo = SqlAlchemyDoctorRepository(db_session)

        doctor_a = Doctor.create(
            organization_id=org_a.id,
            user_id=user_a.id,
            employee_id="EMP-A",
            joining_date=date(2026, 1, 1),
        )
        doctor_b = Doctor.create(
            organization_id=org_b.id,
            user_id=user_b.id,
            employee_id="EMP-B",
            joining_date=date(2026, 1, 1),
        )
        await repo.add(doctor_a)
        await repo.add(doctor_b)
        await db_session.commit()

        doctors_for_a = await repo.list_by_organization(org_a.id)
        assert [d.id for d in doctors_for_a] == [doctor_a.id]


class TestDoctorSearch:
    """Search & Filtering module — `SqlAlchemyDoctorRepository.search`."""

    async def test_scopes_to_organization(self, db_session: AsyncSession) -> None:
        org_a = await persist_organization(db_session)
        org_b = await persist_organization(db_session)
        user_a = await persist_user(db_session, organization_id=org_a.id)
        user_b = await persist_user(db_session, organization_id=org_b.id)
        repo = SqlAlchemyDoctorRepository(db_session)
        doctor_a = Doctor.create(
            organization_id=org_a.id,
            user_id=user_a.id,
            employee_id="EMP-SEARCH-A",
            joining_date=date(2026, 1, 1),
        )
        doctor_b = Doctor.create(
            organization_id=org_b.id,
            user_id=user_b.id,
            employee_id="EMP-SEARCH-B",
            joining_date=date(2026, 1, 1),
        )
        await repo.add(doctor_a)
        await repo.add(doctor_b)
        await db_session.commit()

        results, total = await repo.search(organization_id=org_a.id)

        assert total == 1
        assert [d.id for d in results] == [doctor_a.id]

    async def test_query_matches_employee_id_partially(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        user = await persist_user(db_session, organization_id=organization.id)
        repo = SqlAlchemyDoctorRepository(db_session)
        doctor = Doctor.create(
            organization_id=organization.id,
            user_id=user.id,
            employee_id="EMP-UNIQUE-042",
            joining_date=date(2026, 1, 1),
        )
        await repo.add(doctor)
        await db_session.commit()

        results, total = await repo.search(organization_id=organization.id, query="UNIQUE-042")

        assert total == 1
        assert [d.id for d in results] == [doctor.id]

    async def test_status_filter(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        active_user = await persist_user(db_session, organization_id=organization.id)
        suspended_user = await persist_user(db_session, organization_id=organization.id)
        repo = SqlAlchemyDoctorRepository(db_session)
        active = Doctor.create(
            organization_id=organization.id,
            user_id=active_user.id,
            employee_id="EMP-ACTIVE",
            joining_date=date(2026, 1, 1),
        )
        suspended = Doctor.create(
            organization_id=organization.id,
            user_id=suspended_user.id,
            employee_id="EMP-SUSPENDED",
            joining_date=date(2026, 1, 1),
        )
        suspended.suspend()
        await repo.add(active)
        await repo.add(suspended)
        await db_session.commit()

        results, total = await repo.search(
            organization_id=organization.id, statuses=[DoctorStatus.SUSPENDED]
        )

        assert total == 1
        assert [d.id for d in results] == [suspended.id]

    async def test_pagination_and_sort(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyDoctorRepository(db_session)
        for suffix in ("A", "B", "C"):
            user = await persist_user(db_session, organization_id=organization.id)
            await repo.add(
                Doctor.create(
                    organization_id=organization.id,
                    user_id=user.id,
                    employee_id=f"EMP-PAGE-{suffix}",
                    joining_date=date(2026, 1, 1),
                )
            )
        await db_session.commit()

        first_page, total = await repo.search(
            organization_id=organization.id,
            sort_by="employee_id",
            sort_order="asc",
            offset=0,
            limit=2,
        )
        second_page, _ = await repo.search(
            organization_id=organization.id,
            sort_by="employee_id",
            sort_order="asc",
            offset=2,
            limit=2,
        )

        assert total == 3
        assert [d.employee_id for d in first_page] == ["EMP-PAGE-A", "EMP-PAGE-B"]
        assert [d.employee_id for d in second_page] == ["EMP-PAGE-C"]


class TestDoctorRequiresValidReferences:
    async def test_nonexistent_organization_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        user = await persist_user(db_session, organization_id=organization.id)
        repo = SqlAlchemyDoctorRepository(db_session)

        doctor = Doctor.create(
            organization_id=uuid4(),
            user_id=user.id,
            employee_id="ORPHAN-ORG",
            joining_date=date(2026, 1, 1),
        )
        await repo.add(doctor)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_user_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyDoctorRepository(db_session)

        doctor = Doctor.create(
            organization_id=organization.id,
            user_id=uuid4(),
            employee_id="ORPHAN-USER",
            joining_date=date(2026, 1, 1),
        )
        await repo.add(doctor)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
