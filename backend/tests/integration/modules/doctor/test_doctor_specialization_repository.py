"""Integration tests for `SqlAlchemyDoctorSpecializationRepository`,
including the FKs to `organizations`/`doctors` and the "at most one primary
specialization per doctor" partial unique index, against a real
PostgreSQL instance."""

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.doctor._helpers import persist_organization, persist_user

from app.modules.doctor.domain.entities import Doctor, DoctorSpecialization
from app.modules.doctor.infrastructure.repositories import (
    SqlAlchemyDoctorRepository,
    SqlAlchemyDoctorSpecializationRepository,
)
from app.modules.organization.domain.entities import Organization


async def _persist_doctor(db_session: AsyncSession) -> tuple[Doctor, Organization]:
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
    return doctor, organization


class TestDoctorSpecializationRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        doctor, organization = await _persist_doctor(db_session)
        repo = SqlAlchemyDoctorSpecializationRepository(db_session)

        specialization = DoctorSpecialization.create(
            organization_id=organization.id,
            doctor_id=doctor.id,
            specialization_name="Cardiology",
            years_of_experience=8,
        )
        await repo.add(specialization)
        await db_session.commit()

        reloaded = await repo.get_by_id(specialization.id)
        assert reloaded is not None
        assert reloaded.doctor_id == doctor.id
        assert reloaded.specialization_name == "Cardiology"
        assert reloaded.years_of_experience == 8
        assert reloaded.is_primary is False

    async def test_list_by_doctor_scopes_to_a_single_doctor(self, db_session: AsyncSession) -> None:
        (doctor_a, org_a) = await _persist_doctor(db_session)
        (doctor_b, org_b) = await _persist_doctor(db_session)
        repo = SqlAlchemyDoctorSpecializationRepository(db_session)

        spec_a = DoctorSpecialization.create(
            organization_id=org_a.id, doctor_id=doctor_a.id, specialization_name="Cardiology"
        )
        spec_b = DoctorSpecialization.create(
            organization_id=org_b.id, doctor_id=doctor_b.id, specialization_name="Neurology"
        )
        await repo.add(spec_a)
        await repo.add(spec_b)
        await db_session.commit()

        specs_for_a = await repo.list_by_doctor(doctor_a.id)
        assert [s.id for s in specs_for_a] == [spec_a.id]


class TestUnsetPrimaryForDoctor:
    async def test_clears_is_primary_on_all_of_a_doctors_specializations(
        self, db_session: AsyncSession
    ) -> None:
        doctor, organization = await _persist_doctor(db_session)
        repo = SqlAlchemyDoctorSpecializationRepository(db_session)

        primary = DoctorSpecialization.create(
            organization_id=organization.id,
            doctor_id=doctor.id,
            specialization_name="Cardiology",
            is_primary=True,
        )
        await repo.add(primary)
        await db_session.commit()

        await repo.unset_primary_for_doctor(doctor.id)
        await db_session.commit()

        reloaded = await repo.get_by_id(primary.id)
        assert reloaded is not None
        assert reloaded.is_primary is False


class TestDoctorSpecializationPrimaryUniqueness:
    async def test_two_primary_specializations_for_the_same_doctor_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        doctor, organization = await _persist_doctor(db_session)
        repo = SqlAlchemyDoctorSpecializationRepository(db_session)

        first = DoctorSpecialization.create(
            organization_id=organization.id,
            doctor_id=doctor.id,
            specialization_name="Cardiology",
            is_primary=True,
        )
        await repo.add(first)
        await db_session.commit()

        second = DoctorSpecialization.create(
            organization_id=organization.id,
            doctor_id=doctor.id,
            specialization_name="Neurology",
            is_primary=True,
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestDoctorSpecializationRequiresValidReferences:
    async def test_nonexistent_doctor_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyDoctorSpecializationRepository(db_session)

        specialization = DoctorSpecialization.create(
            organization_id=organization.id,
            doctor_id=uuid4(),
            specialization_name="Orphan Specialization",
        )
        await repo.add(specialization)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
