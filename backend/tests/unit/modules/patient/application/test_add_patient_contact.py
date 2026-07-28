"""Unit tests for the `AddPatientContact` use case, including the "one
primary contact per contact type" invariant."""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.patient.application.dto import AddPatientContactInput
from app.modules.patient.application.use_cases.add_patient_contact import AddPatientContact
from app.modules.patient.domain.entities import Patient
from app.modules.patient.domain.enums import ContactType, Gender
from app.modules.patient.domain.events import PatientContactAdded
from app.modules.patient.domain.exceptions import PatientNotFoundError
from tests.unit.modules.patient.application.fakes import (
    FakePatientContactRepository,
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
def patient_contact_repository() -> FakePatientContactRepository:
    return FakePatientContactRepository()


@pytest.fixture
def patient_repository() -> FakePatientRepository:
    return FakePatientRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def use_case(
    patient_contact_repository: FakePatientContactRepository,
    patient_repository: FakePatientRepository,
    unit_of_work: FakeUnitOfWork,
) -> AddPatientContact:
    return AddPatientContact(
        patient_contact_repository=patient_contact_repository,
        patient_repository=patient_repository,
        unit_of_work=unit_of_work,
    )


class TestAddPatientContact:
    async def test_adds_contact_for_existing_patient(
        self,
        use_case: AddPatientContact,
        patient_repository: FakePatientRepository,
        patient_contact_repository: FakePatientContactRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient = _make_patient()
        await patient_repository.add(patient)

        output = await use_case.execute(
            AddPatientContactInput(
                patient_id=patient.id,
                contact_type=ContactType.MOBILE,
                phone_number="+1 555 0100",
            )
        )

        stored = await patient_contact_repository.get_by_id(output.contact_id)
        assert stored is not None
        assert stored.organization_id == patient.organization_id
        assert unit_of_work.committed is True
        assert any(isinstance(e, PatientContactAdded) for e in unit_of_work.published_events)

    async def test_unknown_patient_raises(self, use_case: AddPatientContact) -> None:
        with pytest.raises(PatientNotFoundError):
            await use_case.execute(
                AddPatientContactInput(
                    patient_id=uuid4(),
                    contact_type=ContactType.MOBILE,
                    phone_number="+1 555 0100",
                )
            )

    async def test_adding_a_new_primary_unsets_the_previous_primary_of_the_same_type(
        self,
        use_case: AddPatientContact,
        patient_repository: FakePatientRepository,
        patient_contact_repository: FakePatientContactRepository,
    ) -> None:
        patient = _make_patient()
        await patient_repository.add(patient)

        first = await use_case.execute(
            AddPatientContactInput(
                patient_id=patient.id,
                contact_type=ContactType.MOBILE,
                phone_number="+1 555 0100",
                is_primary=True,
            )
        )
        second = await use_case.execute(
            AddPatientContactInput(
                patient_id=patient.id,
                contact_type=ContactType.MOBILE,
                phone_number="+1 555 0200",
                is_primary=True,
            )
        )

        stored_first = await patient_contact_repository.get_by_id(first.contact_id)
        stored_second = await patient_contact_repository.get_by_id(second.contact_id)
        assert stored_first is not None
        assert stored_second is not None
        assert stored_first.is_primary is False
        assert stored_second.is_primary is True

    async def test_primary_flags_are_independent_per_contact_type(
        self,
        use_case: AddPatientContact,
        patient_repository: FakePatientRepository,
        patient_contact_repository: FakePatientContactRepository,
    ) -> None:
        patient = _make_patient()
        await patient_repository.add(patient)

        mobile = await use_case.execute(
            AddPatientContactInput(
                patient_id=patient.id,
                contact_type=ContactType.MOBILE,
                phone_number="+1 555 0100",
                is_primary=True,
            )
        )
        home = await use_case.execute(
            AddPatientContactInput(
                patient_id=patient.id,
                contact_type=ContactType.HOME,
                phone_number="+1 555 0200",
                is_primary=True,
            )
        )

        stored_mobile = await patient_contact_repository.get_by_id(mobile.contact_id)
        stored_home = await patient_contact_repository.get_by_id(home.contact_id)
        assert stored_mobile is not None and stored_mobile.is_primary is True
        assert stored_home is not None and stored_home.is_primary is True
