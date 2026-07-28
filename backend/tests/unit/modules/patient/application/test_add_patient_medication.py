"""Unit tests for the `AddPatientMedication` use case, using in-memory
fakes for both this module's own repository and the Doctor module's
public port."""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.doctor.domain.exceptions import DoctorNotFoundError
from app.modules.patient.application.dto import AddPatientMedicationInput
from app.modules.patient.application.use_cases.add_patient_medication import AddPatientMedication
from app.modules.patient.domain.entities import Patient
from app.modules.patient.domain.enums import Gender, RouteOfAdministration
from app.modules.patient.domain.events import PatientMedicationAdded
from app.modules.patient.domain.exceptions import PatientNotFoundError
from tests.unit.modules.patient.application.fakes import (
    FakeDoctorQueryPort,
    FakePatientMedicationRepository,
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


def _make_input(**overrides: object) -> AddPatientMedicationInput:
    defaults: dict[str, object] = {
        "patient_id": uuid4(),
        "medication_name": "Amoxicillin",
        "dosage": "500",
        "route": RouteOfAdministration.ORAL,
        "start_date": date(2026, 1, 1),
    }
    defaults.update(overrides)
    return AddPatientMedicationInput(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def patient_medication_repository() -> FakePatientMedicationRepository:
    return FakePatientMedicationRepository()


@pytest.fixture
def patient_repository() -> FakePatientRepository:
    return FakePatientRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    patient_medication_repository: FakePatientMedicationRepository,
    patient_repository: FakePatientRepository,
    unit_of_work: FakeUnitOfWork,
    *,
    existing_doctor_ids: set[object] | None = None,
) -> AddPatientMedication:
    return AddPatientMedication(
        patient_medication_repository=patient_medication_repository,
        patient_repository=patient_repository,
        doctor_query_port=FakeDoctorQueryPort(
            existing_doctor_ids=existing_doctor_ids  # type: ignore[arg-type]
        ),
        unit_of_work=unit_of_work,
    )


class TestAddPatientMedication:
    async def test_adds_medication_for_existing_patient(
        self,
        patient_medication_repository: FakePatientMedicationRepository,
        patient_repository: FakePatientRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient = _make_patient()
        await patient_repository.add(patient)
        use_case = _use_case(patient_medication_repository, patient_repository, unit_of_work)

        output = await use_case.execute(_make_input(patient_id=patient.id))

        stored = await patient_medication_repository.get_by_id(output.medication_id)
        assert stored is not None
        assert stored.organization_id == patient.organization_id
        assert unit_of_work.committed is True
        assert any(isinstance(e, PatientMedicationAdded) for e in unit_of_work.published_events)

    async def test_unknown_patient_raises(
        self,
        patient_medication_repository: FakePatientMedicationRepository,
        patient_repository: FakePatientRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        use_case = _use_case(patient_medication_repository, patient_repository, unit_of_work)

        with pytest.raises(PatientNotFoundError):
            await use_case.execute(_make_input(patient_id=uuid4()))

    async def test_unknown_prescribing_doctor_raises(
        self,
        patient_medication_repository: FakePatientMedicationRepository,
        patient_repository: FakePatientRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient = _make_patient()
        await patient_repository.add(patient)
        use_case = _use_case(patient_medication_repository, patient_repository, unit_of_work)

        with pytest.raises(DoctorNotFoundError):
            await use_case.execute(_make_input(patient_id=patient.id, prescribed_by=uuid4()))

    async def test_known_prescribing_doctor_is_accepted(
        self,
        patient_medication_repository: FakePatientMedicationRepository,
        patient_repository: FakePatientRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient = _make_patient()
        await patient_repository.add(patient)
        doctor_id = uuid4()
        use_case = _use_case(
            patient_medication_repository,
            patient_repository,
            unit_of_work,
            existing_doctor_ids={doctor_id},
        )

        output = await use_case.execute(_make_input(patient_id=patient.id, prescribed_by=doctor_id))

        stored = await patient_medication_repository.get_by_id(output.medication_id)
        assert stored is not None
        assert stored.prescribed_by == doctor_id

    async def test_medication_without_prescribed_by_is_accepted(
        self,
        patient_medication_repository: FakePatientMedicationRepository,
        patient_repository: FakePatientRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient = _make_patient()
        await patient_repository.add(patient)
        use_case = _use_case(patient_medication_repository, patient_repository, unit_of_work)

        output = await use_case.execute(_make_input(patient_id=patient.id))

        stored = await patient_medication_repository.get_by_id(output.medication_id)
        assert stored is not None
        assert stored.prescribed_by is None

    async def test_multiple_medications_for_the_same_patient_are_allowed(
        self,
        patient_medication_repository: FakePatientMedicationRepository,
        patient_repository: FakePatientRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient = _make_patient()
        await patient_repository.add(patient)
        use_case = _use_case(patient_medication_repository, patient_repository, unit_of_work)

        first = await use_case.execute(
            _make_input(patient_id=patient.id, medication_name="Amoxicillin")
        )
        second = await use_case.execute(
            _make_input(patient_id=patient.id, medication_name="Amoxicillin")
        )

        assert first.medication_id != second.medication_id
        medications = await patient_medication_repository.list_by_patient(patient.id)
        assert len(medications) == 2
