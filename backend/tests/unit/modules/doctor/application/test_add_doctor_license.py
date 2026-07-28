"""Unit tests for the `AddDoctorLicense` use case."""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.doctor.application.dto import AddDoctorLicenseInput
from app.modules.doctor.application.use_cases.add_doctor_license import AddDoctorLicense
from app.modules.doctor.domain.entities import Doctor
from app.modules.doctor.domain.enums import LicenseVerificationStatus
from app.modules.doctor.domain.events import DoctorLicenseAdded
from app.modules.doctor.domain.exceptions import DoctorNotFoundError, DuplicateLicenseNumberError
from tests.unit.modules.doctor.application.fakes import (
    FakeDoctorLicenseRepository,
    FakeDoctorRepository,
    FakeUnitOfWork,
)


def _make_doctor() -> Doctor:
    return Doctor.create(
        organization_id=uuid4(),
        user_id=uuid4(),
        employee_id="EMP-001",
        joining_date=date(2026, 1, 1),
    )


@pytest.fixture
def doctor_license_repository() -> FakeDoctorLicenseRepository:
    return FakeDoctorLicenseRepository()


@pytest.fixture
def doctor_repository() -> FakeDoctorRepository:
    return FakeDoctorRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def use_case(
    doctor_license_repository: FakeDoctorLicenseRepository,
    doctor_repository: FakeDoctorRepository,
    unit_of_work: FakeUnitOfWork,
) -> AddDoctorLicense:
    return AddDoctorLicense(
        doctor_license_repository=doctor_license_repository,
        doctor_repository=doctor_repository,
        unit_of_work=unit_of_work,
    )


class TestAddDoctorLicense:
    async def test_adds_license_for_existing_doctor(
        self,
        use_case: AddDoctorLicense,
        doctor_repository: FakeDoctorRepository,
        doctor_license_repository: FakeDoctorLicenseRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        doctor = _make_doctor()
        await doctor_repository.add(doctor)

        output = await use_case.execute(
            AddDoctorLicenseInput(
                doctor_id=doctor.id,
                license_number="LIC-001",
                issuing_authority="Medical Council",
                country="USA",
                issue_date=date(2020, 1, 1),
                expiry_date=date(2030, 1, 1),
            )
        )

        stored = await doctor_license_repository.get_by_id(output.license_id)
        assert stored is not None
        assert stored.verification_status is LicenseVerificationStatus.PENDING
        assert unit_of_work.committed is True
        assert any(isinstance(e, DoctorLicenseAdded) for e in unit_of_work.published_events)

    async def test_unknown_doctor_raises(self, use_case: AddDoctorLicense) -> None:
        with pytest.raises(DoctorNotFoundError):
            await use_case.execute(
                AddDoctorLicenseInput(
                    doctor_id=uuid4(),
                    license_number="LIC-002",
                    issuing_authority="Medical Council",
                    country="USA",
                    issue_date=date(2020, 1, 1),
                    expiry_date=date(2030, 1, 1),
                )
            )

    async def test_duplicate_license_number_is_rejected(
        self,
        use_case: AddDoctorLicense,
        doctor_repository: FakeDoctorRepository,
    ) -> None:
        first_doctor = _make_doctor()
        second_doctor = _make_doctor()
        await doctor_repository.add(first_doctor)
        await doctor_repository.add(second_doctor)

        await use_case.execute(
            AddDoctorLicenseInput(
                doctor_id=first_doctor.id,
                license_number="LIC-SAME",
                issuing_authority="Medical Council",
                country="USA",
                issue_date=date(2020, 1, 1),
                expiry_date=date(2030, 1, 1),
            )
        )

        with pytest.raises(DuplicateLicenseNumberError):
            await use_case.execute(
                AddDoctorLicenseInput(
                    doctor_id=second_doctor.id,
                    license_number="LIC-SAME",
                    issuing_authority="Medical Council",
                    country="USA",
                    issue_date=date(2020, 1, 1),
                    expiry_date=date(2030, 1, 1),
                )
            )
