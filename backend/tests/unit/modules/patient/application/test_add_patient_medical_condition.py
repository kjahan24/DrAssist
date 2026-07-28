"""Unit tests for the `AddPatientMedicalCondition` use case, using
in-memory fakes for both this module's own repository and the Doctor
module's public port."""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.doctor.domain.exceptions import DoctorNotFoundError
from app.modules.patient.application.dto import AddPatientMedicalConditionInput
from app.modules.patient.application.use_cases.add_patient_medical_condition import (
    AddPatientMedicalCondition,
)
from app.modules.patient.domain.entities import Patient
from app.modules.patient.domain.enums import ConditionSeverity, Gender
from app.modules.patient.domain.events import PatientMedicalConditionRecorded
from app.modules.patient.domain.exceptions import (
    DuplicateActiveConditionError,
    PatientNotFoundError,
)
from tests.unit.modules.patient.application.fakes import (
    FakeDoctorQueryPort,
    FakePatientMedicalConditionRepository,
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


def _make_input(**overrides: object) -> AddPatientMedicalConditionInput:
    defaults: dict[str, object] = {
        "patient_id": uuid4(),
        "condition_name": "Type 2 Diabetes",
        "category": "Endocrine",
        "severity": ConditionSeverity.MODERATE,
        "diagnosis_date": date(2026, 1, 1),
    }
    defaults.update(overrides)
    return AddPatientMedicalConditionInput(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def patient_medical_condition_repository() -> FakePatientMedicalConditionRepository:
    return FakePatientMedicalConditionRepository()


@pytest.fixture
def patient_repository() -> FakePatientRepository:
    return FakePatientRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    patient_medical_condition_repository: FakePatientMedicalConditionRepository,
    patient_repository: FakePatientRepository,
    unit_of_work: FakeUnitOfWork,
    *,
    existing_doctor_ids: set[object] | None = None,
) -> AddPatientMedicalCondition:
    return AddPatientMedicalCondition(
        patient_medical_condition_repository=patient_medical_condition_repository,
        patient_repository=patient_repository,
        doctor_query_port=FakeDoctorQueryPort(
            existing_doctor_ids=existing_doctor_ids  # type: ignore[arg-type]
        ),
        unit_of_work=unit_of_work,
    )


class TestAddPatientMedicalCondition:
    async def test_adds_condition_for_existing_patient(
        self,
        patient_medical_condition_repository: FakePatientMedicalConditionRepository,
        patient_repository: FakePatientRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient = _make_patient()
        await patient_repository.add(patient)
        use_case = _use_case(patient_medical_condition_repository, patient_repository, unit_of_work)

        output = await use_case.execute(_make_input(patient_id=patient.id))

        stored = await patient_medical_condition_repository.get_by_id(output.condition_id)
        assert stored is not None
        assert stored.organization_id == patient.organization_id
        assert unit_of_work.committed is True
        assert any(
            isinstance(e, PatientMedicalConditionRecorded) for e in unit_of_work.published_events
        )

    async def test_unknown_patient_raises(
        self,
        patient_medical_condition_repository: FakePatientMedicalConditionRepository,
        patient_repository: FakePatientRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        use_case = _use_case(patient_medical_condition_repository, patient_repository, unit_of_work)

        with pytest.raises(PatientNotFoundError):
            await use_case.execute(_make_input(patient_id=uuid4()))

    async def test_unknown_diagnosing_doctor_raises(
        self,
        patient_medical_condition_repository: FakePatientMedicalConditionRepository,
        patient_repository: FakePatientRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient = _make_patient()
        await patient_repository.add(patient)
        use_case = _use_case(patient_medical_condition_repository, patient_repository, unit_of_work)

        with pytest.raises(DoctorNotFoundError):
            await use_case.execute(_make_input(patient_id=patient.id, diagnosed_by=uuid4()))

    async def test_known_diagnosing_doctor_is_accepted(
        self,
        patient_medical_condition_repository: FakePatientMedicalConditionRepository,
        patient_repository: FakePatientRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient = _make_patient()
        await patient_repository.add(patient)
        doctor_id = uuid4()
        use_case = _use_case(
            patient_medical_condition_repository,
            patient_repository,
            unit_of_work,
            existing_doctor_ids={doctor_id},
        )

        output = await use_case.execute(_make_input(patient_id=patient.id, diagnosed_by=doctor_id))

        stored = await patient_medical_condition_repository.get_by_id(output.condition_id)
        assert stored is not None
        assert stored.diagnosed_by == doctor_id

    async def test_duplicate_active_condition_for_the_same_name_is_rejected(
        self,
        patient_medical_condition_repository: FakePatientMedicalConditionRepository,
        patient_repository: FakePatientRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient = _make_patient()
        await patient_repository.add(patient)
        use_case = _use_case(patient_medical_condition_repository, patient_repository, unit_of_work)

        await use_case.execute(_make_input(patient_id=patient.id, condition_name="Type 2 Diabetes"))

        with pytest.raises(DuplicateActiveConditionError):
            await use_case.execute(
                _make_input(patient_id=patient.id, condition_name="Type 2 Diabetes")
            )

    async def test_resolved_condition_does_not_block_a_new_active_one(
        self,
        patient_medical_condition_repository: FakePatientMedicalConditionRepository,
        patient_repository: FakePatientRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient = _make_patient()
        await patient_repository.add(patient)
        use_case = _use_case(patient_medical_condition_repository, patient_repository, unit_of_work)

        first_output = await use_case.execute(
            _make_input(patient_id=patient.id, condition_name="Bronchitis")
        )
        first_condition = await patient_medical_condition_repository.get_by_id(
            first_output.condition_id
        )
        assert first_condition is not None
        first_condition.resolve(resolved_date=date(2026, 2, 1))

        second_output = await use_case.execute(
            _make_input(patient_id=patient.id, condition_name="Bronchitis")
        )
        assert second_output.condition_id != first_output.condition_id
