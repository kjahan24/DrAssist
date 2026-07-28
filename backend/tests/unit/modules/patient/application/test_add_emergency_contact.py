"""Unit tests for the `AddEmergencyContact` use case, including the "one
primary emergency contact" invariant."""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.patient.application.dto import AddEmergencyContactInput
from app.modules.patient.application.use_cases.add_emergency_contact import AddEmergencyContact
from app.modules.patient.domain.entities import Patient
from app.modules.patient.domain.enums import Gender
from app.modules.patient.domain.events import EmergencyContactAdded
from app.modules.patient.domain.exceptions import PatientNotFoundError
from tests.unit.modules.patient.application.fakes import (
    FakeEmergencyContactRepository,
    FakePatientRepository,
    FakeUnitOfWork,
)


def _make_patient() -> Patient:
    return Patient.register(
        organization_id=uuid4(),
        patient_number="PAT-001",
        first_name="Jane",
        last_name="Doe",
        gender=Gender.FEMALE,
        date_of_birth=date(1990, 1, 1),
    )


@pytest.fixture
def emergency_contact_repository() -> FakeEmergencyContactRepository:
    return FakeEmergencyContactRepository()


@pytest.fixture
def patient_repository() -> FakePatientRepository:
    return FakePatientRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def use_case(
    emergency_contact_repository: FakeEmergencyContactRepository,
    patient_repository: FakePatientRepository,
    unit_of_work: FakeUnitOfWork,
) -> AddEmergencyContact:
    return AddEmergencyContact(
        emergency_contact_repository=emergency_contact_repository,
        patient_repository=patient_repository,
        unit_of_work=unit_of_work,
    )


class TestAddEmergencyContact:
    async def test_adds_contact_for_existing_patient(
        self,
        use_case: AddEmergencyContact,
        patient_repository: FakePatientRepository,
        emergency_contact_repository: FakeEmergencyContactRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient = _make_patient()
        await patient_repository.add(patient)

        output = await use_case.execute(
            AddEmergencyContactInput(
                patient_id=patient.id,
                full_name="John Doe",
                relationship="Spouse",
                phone_number="+1 555 0100",
            )
        )

        stored = await emergency_contact_repository.get_by_id(output.contact_id)
        assert stored is not None
        assert stored.organization_id == patient.organization_id
        assert unit_of_work.committed is True
        assert any(isinstance(e, EmergencyContactAdded) for e in unit_of_work.published_events)

    async def test_unknown_patient_raises(self, use_case: AddEmergencyContact) -> None:
        with pytest.raises(PatientNotFoundError):
            await use_case.execute(
                AddEmergencyContactInput(
                    patient_id=uuid4(),
                    full_name="John Doe",
                    relationship="Spouse",
                    phone_number="+1 555 0100",
                )
            )

    async def test_adding_a_new_primary_unsets_the_previous_primary(
        self,
        use_case: AddEmergencyContact,
        patient_repository: FakePatientRepository,
        emergency_contact_repository: FakeEmergencyContactRepository,
    ) -> None:
        patient = _make_patient()
        await patient_repository.add(patient)

        first = await use_case.execute(
            AddEmergencyContactInput(
                patient_id=patient.id,
                full_name="John Doe",
                relationship="Spouse",
                phone_number="+1 555 0100",
                is_primary=True,
            )
        )
        second = await use_case.execute(
            AddEmergencyContactInput(
                patient_id=patient.id,
                full_name="Jane Smith",
                relationship="Sister",
                phone_number="+1 555 0200",
                is_primary=True,
            )
        )

        stored_first = await emergency_contact_repository.get_by_id(first.contact_id)
        stored_second = await emergency_contact_repository.get_by_id(second.contact_id)
        assert stored_first is not None
        assert stored_second is not None
        assert stored_first.is_primary is False
        assert stored_second.is_primary is True
