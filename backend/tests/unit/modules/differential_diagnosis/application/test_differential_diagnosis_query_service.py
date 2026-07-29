"""Unit tests for `DifferentialDiagnosisQueryService` — backs the
module's public `DifferentialDiagnosisQueryPort` facade."""

from uuid import uuid4

import pytest

from app.modules.differential_diagnosis.application.services.differential_diagnosis_query_service import (  # noqa: E501
    DifferentialDiagnosisQueryService,
)
from app.modules.differential_diagnosis.domain.entities import DifferentialDiagnosis
from app.modules.differential_diagnosis.domain.enums import DiagnosisSource
from tests.unit.modules.differential_diagnosis.application.fakes import (
    FakeDifferentialDiagnosisRepository,
)


def _make_diagnosis(**overrides: object) -> DifferentialDiagnosis:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "clinical_note_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "diagnosis_name": "Community-acquired pneumonia",
        "diagnosis_source": DiagnosisSource.AI,
        "ranking": 1,
    }
    defaults.update(overrides)
    return DifferentialDiagnosis.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def repo() -> FakeDifferentialDiagnosisRepository:
    return FakeDifferentialDiagnosisRepository()


@pytest.fixture
def service(repo: FakeDifferentialDiagnosisRepository) -> DifferentialDiagnosisQueryService:
    return DifferentialDiagnosisQueryService(differential_diagnosis_repository=repo)


class TestDifferentialDiagnosisExists:
    async def test_true_for_a_known_diagnosis(
        self, service: DifferentialDiagnosisQueryService, repo: FakeDifferentialDiagnosisRepository
    ) -> None:
        diagnosis = _make_diagnosis()
        await repo.add(diagnosis)
        assert await service.differential_diagnosis_exists(diagnosis.id) is True

    async def test_false_for_an_unknown_diagnosis(
        self, service: DifferentialDiagnosisQueryService
    ) -> None:
        assert await service.differential_diagnosis_exists(uuid4()) is False


class TestIsEditable:
    async def test_true_while_pending(
        self, service: DifferentialDiagnosisQueryService, repo: FakeDifferentialDiagnosisRepository
    ) -> None:
        diagnosis = _make_diagnosis(diagnosis_source=DiagnosisSource.AI)
        await repo.add(diagnosis)
        assert await service.is_editable(diagnosis.id) is True

    async def test_true_while_reviewed(
        self, service: DifferentialDiagnosisQueryService, repo: FakeDifferentialDiagnosisRepository
    ) -> None:
        diagnosis = _make_diagnosis(diagnosis_source=DiagnosisSource.PHYSICIAN)
        await repo.add(diagnosis)
        assert await service.is_editable(diagnosis.id) is True

    async def test_false_once_approved(
        self, service: DifferentialDiagnosisQueryService, repo: FakeDifferentialDiagnosisRepository
    ) -> None:
        diagnosis = _make_diagnosis()
        diagnosis.approve()
        await repo.add(diagnosis)
        assert await service.is_editable(diagnosis.id) is False

    async def test_false_once_rejected(
        self, service: DifferentialDiagnosisQueryService, repo: FakeDifferentialDiagnosisRepository
    ) -> None:
        diagnosis = _make_diagnosis()
        diagnosis.reject()
        await repo.add(diagnosis)
        assert await service.is_editable(diagnosis.id) is False

    async def test_false_for_an_unknown_diagnosis(
        self, service: DifferentialDiagnosisQueryService
    ) -> None:
        assert await service.is_editable(uuid4()) is False


class TestGetDifferentialDiagnosisSummary:
    async def test_returns_summary_for_a_known_diagnosis(
        self, service: DifferentialDiagnosisQueryService, repo: FakeDifferentialDiagnosisRepository
    ) -> None:
        diagnosis = _make_diagnosis(likelihood_score=0.7, excluded=True)
        await repo.add(diagnosis)

        summary = await service.get_differential_diagnosis_summary(diagnosis.id)

        assert summary is not None
        assert summary.differential_diagnosis_id == diagnosis.id
        assert summary.organization_id == diagnosis.organization_id
        assert summary.patient_id == diagnosis.patient_id
        assert summary.visit_id == diagnosis.visit_id
        assert summary.doctor_id == diagnosis.doctor_id
        assert summary.likelihood_score == 0.7
        assert summary.excluded is True

    async def test_returns_none_for_an_unknown_diagnosis(
        self, service: DifferentialDiagnosisQueryService
    ) -> None:
        assert await service.get_differential_diagnosis_summary(uuid4()) is None


class TestListDifferentialDiagnosesForClinicalNote:
    async def test_returns_diagnoses_scoped_to_the_clinical_note_ordered_by_ranking(
        self, service: DifferentialDiagnosisQueryService, repo: FakeDifferentialDiagnosisRepository
    ) -> None:
        clinical_note_id = uuid4()
        await repo.add(
            _make_diagnosis(clinical_note_id=clinical_note_id, diagnosis_name="Second", ranking=2)
        )
        await repo.add(
            _make_diagnosis(clinical_note_id=clinical_note_id, diagnosis_name="First", ranking=1)
        )
        await repo.add(_make_diagnosis(diagnosis_name="Other note"))

        summaries = await service.list_differential_diagnoses_for_clinical_note(clinical_note_id)

        assert [s.diagnosis_name for s in summaries] == ["First", "Second"]

    async def test_returns_empty_list_for_a_clinical_note_without_diagnoses(
        self, service: DifferentialDiagnosisQueryService
    ) -> None:
        assert await service.list_differential_diagnoses_for_clinical_note(uuid4()) == []


class TestListDifferentialDiagnosesForPatient:
    async def test_returns_diagnoses_scoped_to_the_patient(
        self, service: DifferentialDiagnosisQueryService, repo: FakeDifferentialDiagnosisRepository
    ) -> None:
        patient_id = uuid4()
        await repo.add(_make_diagnosis(patient_id=patient_id, diagnosis_name="A"))
        await repo.add(_make_diagnosis(diagnosis_name="B"))

        summaries = await service.list_differential_diagnoses_for_patient(patient_id)

        assert [s.diagnosis_name for s in summaries] == ["A"]

    async def test_returns_empty_list_for_a_patient_without_diagnoses(
        self, service: DifferentialDiagnosisQueryService
    ) -> None:
        assert await service.list_differential_diagnoses_for_patient(uuid4()) == []
