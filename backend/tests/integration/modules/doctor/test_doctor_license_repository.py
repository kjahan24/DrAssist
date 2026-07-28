"""Integration tests for `SqlAlchemyDoctorLicenseRepository`, including the
FK to `doctors` and the global `license_number` uniqueness constraint,
against a real PostgreSQL instance."""

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.doctor._helpers import persist_organization, persist_user

from app.modules.doctor.domain.entities import Doctor, DoctorLicense
from app.modules.doctor.domain.enums import LicenseVerificationStatus
from app.modules.doctor.infrastructure.repositories import (
    SqlAlchemyDoctorLicenseRepository,
    SqlAlchemyDoctorRepository,
)


async def _persist_doctor(db_session: AsyncSession, *, employee_id: str = "EMP-001") -> Doctor:
    organization = await persist_organization(db_session)
    user = await persist_user(db_session, organization_id=organization.id)
    repo = SqlAlchemyDoctorRepository(db_session)
    doctor = Doctor.create(
        organization_id=organization.id,
        user_id=user.id,
        employee_id=employee_id,
        joining_date=date(2026, 1, 1),
    )
    await repo.add(doctor)
    await db_session.commit()
    return doctor


def _unique_license_number() -> str:
    return f"LIC-{uuid4().hex[:12].upper()}"


class TestDoctorLicenseRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        doctor = await _persist_doctor(db_session)
        repo = SqlAlchemyDoctorLicenseRepository(db_session)
        license_number = _unique_license_number()

        license_ = DoctorLicense.create(
            doctor_id=doctor.id,
            license_number=license_number,
            issuing_authority="Medical Council",
            country="USA",
            issue_date=date(2020, 1, 1),
            expiry_date=date(2030, 1, 1),
        )
        await repo.add(license_)
        await db_session.commit()

        reloaded = await repo.get_by_id(license_.id)
        assert reloaded is not None
        assert reloaded.doctor_id == doctor.id
        assert reloaded.license_number == license_number
        assert reloaded.verification_status is LicenseVerificationStatus.PENDING

    async def test_verification_status_change_persists(self, db_session: AsyncSession) -> None:
        doctor = await _persist_doctor(db_session)
        repo = SqlAlchemyDoctorLicenseRepository(db_session)

        license_ = DoctorLicense.create(
            doctor_id=doctor.id,
            license_number=_unique_license_number(),
            issuing_authority="Medical Council",
            country="USA",
            issue_date=date(2020, 1, 1),
            expiry_date=date(2030, 1, 1),
        )
        await repo.add(license_)
        await db_session.commit()

        license_.verify()
        await repo.add(license_)
        await db_session.commit()

        reloaded = await repo.get_by_id(license_.id)
        assert reloaded is not None
        assert reloaded.verification_status is LicenseVerificationStatus.VERIFIED

    async def test_get_by_license_number_finds_it(self, db_session: AsyncSession) -> None:
        doctor = await _persist_doctor(db_session)
        repo = SqlAlchemyDoctorLicenseRepository(db_session)
        license_number = _unique_license_number()

        license_ = DoctorLicense.create(
            doctor_id=doctor.id,
            license_number=license_number,
            issuing_authority="Medical Council",
            country="USA",
            issue_date=date(2020, 1, 1),
            expiry_date=date(2030, 1, 1),
        )
        await repo.add(license_)
        await db_session.commit()

        reloaded = await repo.get_by_license_number(license_number)
        assert reloaded is not None
        assert reloaded.id == license_.id

    async def test_list_by_doctor_scopes_to_a_single_doctor(self, db_session: AsyncSession) -> None:
        doctor_a = await _persist_doctor(db_session, employee_id="EMP-A")
        doctor_b = await _persist_doctor(db_session, employee_id="EMP-B")
        repo = SqlAlchemyDoctorLicenseRepository(db_session)

        license_a = DoctorLicense.create(
            doctor_id=doctor_a.id,
            license_number=_unique_license_number(),
            issuing_authority="Medical Council",
            country="USA",
            issue_date=date(2020, 1, 1),
            expiry_date=date(2030, 1, 1),
        )
        license_b = DoctorLicense.create(
            doctor_id=doctor_b.id,
            license_number=_unique_license_number(),
            issuing_authority="Medical Council",
            country="USA",
            issue_date=date(2020, 1, 1),
            expiry_date=date(2030, 1, 1),
        )
        await repo.add(license_a)
        await repo.add(license_b)
        await db_session.commit()

        licenses_for_a = await repo.list_by_doctor(doctor_a.id)
        assert [lic.id for lic in licenses_for_a] == [license_a.id]


class TestDoctorLicenseUniqueness:
    async def test_duplicate_license_number_violates_unique_constraint(
        self, db_session: AsyncSession
    ) -> None:
        doctor_a = await _persist_doctor(db_session, employee_id="EMP-A")
        doctor_b = await _persist_doctor(db_session, employee_id="EMP-B")
        repo = SqlAlchemyDoctorLicenseRepository(db_session)
        license_number = _unique_license_number()

        first = DoctorLicense.create(
            doctor_id=doctor_a.id,
            license_number=license_number,
            issuing_authority="Medical Council",
            country="USA",
            issue_date=date(2020, 1, 1),
            expiry_date=date(2030, 1, 1),
        )
        await repo.add(first)
        await db_session.commit()

        second = DoctorLicense.create(
            doctor_id=doctor_b.id,
            license_number=license_number,
            issuing_authority="Medical Council",
            country="USA",
            issue_date=date(2020, 1, 1),
            expiry_date=date(2030, 1, 1),
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestDoctorLicenseRequiresValidDoctor:
    async def test_nonexistent_doctor_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyDoctorLicenseRepository(db_session)
        license_ = DoctorLicense.create(
            doctor_id=uuid4(),
            license_number=_unique_license_number(),
            issuing_authority="Medical Council",
            country="USA",
            issue_date=date(2020, 1, 1),
            expiry_date=date(2030, 1, 1),
        )
        await repo.add(license_)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
