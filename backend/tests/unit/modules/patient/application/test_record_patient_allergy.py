"""Unit tests for the `RecordPatientAllergy` use case, using in-memory
fakes for both this module's own repository and the Doctor module's
public port."""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.doctor.domain.exceptions import DoctorNotFoundError
from app.modules.patient.application.dto import RecordPatientAllergyInput
from app.modules.patient.application.use_cases.record_patient_allergy import RecordPatientAllergy
from app.modules.patient.domain.entities import Patient
from app.modules.patient.domain.enums import AllergySeverity, AllergyType, Gender
from app.modules.patient.domain.events import PatientAllergyRecorded
from app.modules.patient.domain.exceptions import DuplicateActiveAllergyError, PatientNotFoundError
from tests.unit.modules.patient.application.fakes import (
    FakeDoctorQueryPort,
    FakePatientAllergyRepository,
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


def _make_input(**overrides: object) -> RecordPatientAllergyInput:
    defaults: dict[str, object] = {
        "patient_id": uuid4(),
        "allergy_type": AllergyType.DRUG,
        "allergen_name": "Penicillin",
        "severity": AllergySeverity.SEVERE,
    }
    defaults.update(overrides)
    return RecordPatientAllergyInput(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def patient_allergy_repository() -> FakePatientAllergyRepository:
    return FakePatientAllergyRepository()


@pytest.fixture
def patient_repository() -> FakePatientRepository:
    return FakePatientRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    patient_allergy_repository: FakePatientAllergyRepository,
    patient_repository: FakePatientRepository,
    unit_of_work: FakeUnitOfWork,
    *,
    existing_doctor_ids: set[object] | None = None,
) -> RecordPatientAllergy:
    return RecordPatientAllergy(
        patient_allergy_repository=patient_allergy_repository,
        patient_repository=patient_repository,
        doctor_query_port=FakeDoctorQueryPort(
            existing_doctor_ids=existing_doctor_ids  # type: ignore[arg-type]
        ),
        unit_of_work=unit_of_work,
    )


class TestRecordPatientAllergy:
    async def test_records_allergy_for_existing_patient(
        self,
        patient_allergy_repository: FakePatientAllergyRepository,
        patient_repository: FakePatientRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient = _make_patient()
        await patient_repository.add(patient)
        use_case = _use_case(patient_allergy_repository, patient_repository, unit_of_work)

        output = await use_case.execute(_make_input(patient_id=patient.id))

        stored = await patient_allergy_repository.get_by_id(output.allergy_id)
        assert stored is not None
        assert stored.organization_id == patient.organization_id
        assert unit_of_work.committed is True
        assert any(isinstance(e, PatientAllergyRecorded) for e in unit_of_work.published_events)

    async def test_unknown_patient_raises(
        self,
        patient_allergy_repository: FakePatientAllergyRepository,
        patient_repository: FakePatientRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        use_case = _use_case(patient_allergy_repository, patient_repository, unit_of_work)

        with pytest.raises(PatientNotFoundError):
            await use_case.execute(_make_input(patient_id=uuid4()))

    async def test_unknown_verifying_doctor_raises(
        self,
        patient_allergy_repository: FakePatientAllergyRepository,
        patient_repository: FakePatientRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient = _make_patient()
        await patient_repository.add(patient)
        use_case = _use_case(patient_allergy_repository, patient_repository, unit_of_work)

        with pytest.raises(DoctorNotFoundError):
            await use_case.execute(_make_input(patient_id=patient.id, verified_by=uuid4()))

    async def test_known_verifying_doctor_is_accepted(
        self,
        patient_allergy_repository: FakePatientAllergyRepository,
        patient_repository: FakePatientRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient = _make_patient()
        await patient_repository.add(patient)
        doctor_id = uuid4()
        use_case = _use_case(
            patient_allergy_repository,
            patient_repository,
            unit_of_work,
            existing_doctor_ids={doctor_id},
        )

        output = await use_case.execute(_make_input(patient_id=patient.id, verified_by=doctor_id))

        stored = await patient_allergy_repository.get_by_id(output.allergy_id)
        assert stored is not None
        assert stored.verified_by == doctor_id

    async def test_duplicate_active_allergy_for_the_same_allergen_is_rejected(
        self,
        patient_allergy_repository: FakePatientAllergyRepository,
        patient_repository: FakePatientRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient = _make_patient()
        await patient_repository.add(patient)
        use_case = _use_case(patient_allergy_repository, patient_repository, unit_of_work)

        await use_case.execute(_make_input(patient_id=patient.id, allergen_name="Penicillin"))

        with pytest.raises(DuplicateActiveAllergyError):
            await use_case.execute(_make_input(patient_id=patient.id, allergen_name="Penicillin"))

    async def test_resolved_allergy_does_not_block_a_new_active_one(
        self,
        patient_allergy_repository: FakePatientAllergyRepository,
        patient_repository: FakePatientRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient = _make_patient()
        await patient_repository.add(patient)
        use_case = _use_case(patient_allergy_repository, patient_repository, unit_of_work)

        first_output = await use_case.execute(
            _make_input(patient_id=patient.id, allergen_name="Penicillin")
        )
        first_allergy = await patient_allergy_repository.get_by_id(first_output.allergy_id)
        assert first_allergy is not None
        first_allergy.resolve()

        second_output = await use_case.execute(
            _make_input(patient_id=patient.id, allergen_name="Penicillin")
        )
        assert second_output.allergy_id != first_output.allergy_id
