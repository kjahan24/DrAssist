"""Integration tests for `SqlAlchemyDoctorProfileRepository`, including the
FK to `doctors`, against a real PostgreSQL instance."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.doctor._helpers import persist_organization, persist_user

from app.modules.doctor.domain.entities import Doctor, DoctorProfile
from app.modules.doctor.domain.enums import Gender
from app.modules.doctor.infrastructure.repositories import (
    SqlAlchemyDoctorProfileRepository,
    SqlAlchemyDoctorRepository,
)
from app.shared.domain.common_value_objects import EmailAddress


async def _persist_doctor(db_session: AsyncSession) -> Doctor:
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
    return doctor


class TestDoctorProfileRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        doctor = await _persist_doctor(db_session)
        repo = SqlAlchemyDoctorProfileRepository(db_session)

        profile = DoctorProfile.create(
            doctor_id=doctor.id,
            full_name="Dr. Jane Doe",
            gender=Gender.FEMALE,
            date_of_birth=date(1985, 5, 1),
            phone="+1-555-0100",
            email=EmailAddress("jane.doe@example.com"),
            years_of_experience=10,
            consultation_fee=Decimal("150.00"),
        )
        await repo.add(profile)
        await db_session.commit()

        reloaded = await repo.get_by_doctor_id(doctor.id)
        assert reloaded is not None
        assert reloaded.full_name == "Dr. Jane Doe"
        assert reloaded.gender is Gender.FEMALE
        assert str(reloaded.email) == "jane.doe@example.com"
        assert reloaded.years_of_experience == 10
        assert reloaded.consultation_fee == Decimal("150.00")

    async def test_update_persists(self, db_session: AsyncSession) -> None:
        doctor = await _persist_doctor(db_session)
        repo = SqlAlchemyDoctorProfileRepository(db_session)

        profile = DoctorProfile.create(
            doctor_id=doctor.id,
            full_name="Dr. Jane Doe",
            gender=Gender.FEMALE,
            date_of_birth=date(1985, 5, 1),
        )
        await repo.add(profile)
        await db_session.commit()

        profile.update(full_name="Dr. Jane A. Doe", years_of_experience=12)
        await repo.add(profile)
        await db_session.commit()

        reloaded = await repo.get_by_doctor_id(doctor.id)
        assert reloaded is not None
        assert reloaded.full_name == "Dr. Jane A. Doe"
        assert reloaded.years_of_experience == 12


class TestDoctorProfileRequiresValidDoctor:
    async def test_nonexistent_doctor_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyDoctorProfileRepository(db_session)
        profile = DoctorProfile.create(
            doctor_id=uuid4(),
            full_name="Orphan Profile",
            gender=Gender.OTHER,
            date_of_birth=date(1990, 1, 1),
        )
        await repo.add(profile)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
