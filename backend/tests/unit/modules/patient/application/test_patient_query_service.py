"""Unit tests for `PatientQueryService` — backs the module's public
`PatientQueryPort` facade."""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.patient.application.services.patient_query_service import PatientQueryService
from app.modules.patient.domain.entities import Patient
from app.modules.patient.domain.enums import Gender
from tests.unit.modules.patient.application.fakes import FakePatientRepository


def _make_patient(**overrides: object) -> Patient:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_number": "PAT-001",
        "first_name": "Jane",
        "last_name": "Doe",
        "gender": Gender.FEMALE,
        "date_of_birth": date(1990, 1, 1),
    }
    defaults.update(overrides)
    return Patient.register(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def patient_repository() -> FakePatientRepository:
    return FakePatientRepository()


@pytest.fixture
def service(patient_repository: FakePatientRepository) -> PatientQueryService:
    return PatientQueryService(patient_repository=patient_repository)


class TestPatientExists:
    async def test_true_for_a_known_patient(
        self, service: PatientQueryService, patient_repository: FakePatientRepository
    ) -> None:
        patient = _make_patient()
        await patient_repository.add(patient)
        assert await service.patient_exists(patient.id) is True

    async def test_false_for_an_unknown_patient(self, service: PatientQueryService) -> None:
        assert await service.patient_exists(uuid4()) is False


class TestIsActive:
    async def test_reflects_the_patients_status(
        self, service: PatientQueryService, patient_repository: FakePatientRepository
    ) -> None:
        patient = _make_patient()
        await patient_repository.add(patient)
        assert await service.is_active(patient.id) is True

        patient.deactivate()
        await patient_repository.add(patient)
        assert await service.is_active(patient.id) is False

    async def test_false_for_an_unknown_patient(self, service: PatientQueryService) -> None:
        assert await service.is_active(uuid4()) is False


class TestGetPatientSummary:
    async def test_returns_summary_for_known_patient(
        self, service: PatientQueryService, patient_repository: FakePatientRepository
    ) -> None:
        patient = _make_patient(patient_number="PAT-42")
        await patient_repository.add(patient)

        summary = await service.get_patient_summary(patient.id)

        assert summary is not None
        assert summary.patient_number == "PAT-42"
        assert summary.organization_id == patient.organization_id
        assert summary.first_name == "Jane"
        assert summary.last_name == "Doe"

    async def test_returns_none_for_unknown_patient(self, service: PatientQueryService) -> None:
        assert await service.get_patient_summary(uuid4()) is None
