"""Unit tests for the `AddDoctorSpecialization` use case, including the
"at most one primary specialization per doctor" invariant."""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.doctor.application.dto import AddDoctorSpecializationInput
from app.modules.doctor.application.use_cases.add_doctor_specialization import (
    AddDoctorSpecialization,
)
from app.modules.doctor.domain.entities import Doctor
from app.modules.doctor.domain.events import DoctorSpecializationAdded
from app.modules.doctor.domain.exceptions import DoctorNotFoundError
from tests.unit.modules.doctor.application.fakes import (
    FakeDoctorRepository,
    FakeDoctorSpecializationRepository,
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
def doctor_specialization_repository() -> FakeDoctorSpecializationRepository:
    return FakeDoctorSpecializationRepository()


@pytest.fixture
def doctor_repository() -> FakeDoctorRepository:
    return FakeDoctorRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def use_case(
    doctor_specialization_repository: FakeDoctorSpecializationRepository,
    doctor_repository: FakeDoctorRepository,
    unit_of_work: FakeUnitOfWork,
) -> AddDoctorSpecialization:
    return AddDoctorSpecialization(
        doctor_specialization_repository=doctor_specialization_repository,
        doctor_repository=doctor_repository,
        unit_of_work=unit_of_work,
    )


class TestAddDoctorSpecialization:
    async def test_adds_specialization_for_existing_doctor(
        self,
        use_case: AddDoctorSpecialization,
        doctor_repository: FakeDoctorRepository,
        doctor_specialization_repository: FakeDoctorSpecializationRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        doctor = _make_doctor()
        await doctor_repository.add(doctor)

        output = await use_case.execute(
            AddDoctorSpecializationInput(doctor_id=doctor.id, specialization_name="Cardiology")
        )

        stored = await doctor_specialization_repository.get_by_id(output.specialization_id)
        assert stored is not None
        assert stored.organization_id == doctor.organization_id
        assert unit_of_work.committed is True
        assert any(isinstance(e, DoctorSpecializationAdded) for e in unit_of_work.published_events)

    async def test_unknown_doctor_raises(self, use_case: AddDoctorSpecialization) -> None:
        with pytest.raises(DoctorNotFoundError):
            await use_case.execute(
                AddDoctorSpecializationInput(doctor_id=uuid4(), specialization_name="Cardiology")
            )

    async def test_adding_a_new_primary_unsets_the_previous_primary(
        self,
        use_case: AddDoctorSpecialization,
        doctor_repository: FakeDoctorRepository,
        doctor_specialization_repository: FakeDoctorSpecializationRepository,
    ) -> None:
        doctor = _make_doctor()
        await doctor_repository.add(doctor)

        first = await use_case.execute(
            AddDoctorSpecializationInput(
                doctor_id=doctor.id, specialization_name="Cardiology", is_primary=True
            )
        )
        second = await use_case.execute(
            AddDoctorSpecializationInput(
                doctor_id=doctor.id, specialization_name="Neurology", is_primary=True
            )
        )

        stored_first = await doctor_specialization_repository.get_by_id(first.specialization_id)
        stored_second = await doctor_specialization_repository.get_by_id(second.specialization_id)
        assert stored_first is not None
        assert stored_second is not None
        assert stored_first.is_primary is False
        assert stored_second.is_primary is True
