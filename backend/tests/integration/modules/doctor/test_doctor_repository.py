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
