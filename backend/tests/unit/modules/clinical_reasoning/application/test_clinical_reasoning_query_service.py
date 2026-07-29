"""Unit tests for `ClinicalReasoningQueryService` — backs the module's
public `ClinicalReasoningQueryPort` facade."""

from uuid import uuid4

import pytest

from app.modules.clinical_reasoning.application.services.clinical_reasoning_query_service import (
    ClinicalReasoningQueryService,
)
from app.modules.clinical_reasoning.domain.entities import ClinicalReasoning
from app.modules.clinical_reasoning.domain.enums import ReasoningSource
from tests.unit.modules.clinical_reasoning.application.fakes import (
    FakeClinicalReasoningRepository,
)


def _make_reasoning(**overrides: object) -> ClinicalReasoning:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "clinical_note_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "reasoning_source": ReasoningSource.AI,
        "reasoning_text": "Elevated WBC suggests possible infection.",
        "ai_generated": True,
    }
    defaults.update(overrides)
    return ClinicalReasoning.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def repo() -> FakeClinicalReasoningRepository:
    return FakeClinicalReasoningRepository()


@pytest.fixture
def service(repo: FakeClinicalReasoningRepository) -> ClinicalReasoningQueryService:
    return ClinicalReasoningQueryService(clinical_reasoning_repository=repo)


class TestClinicalReasoningExists:
    async def test_true_for_a_known_record(
        self, service: ClinicalReasoningQueryService, repo: FakeClinicalReasoningRepository
    ) -> None:
        reasoning = _make_reasoning()
        await repo.add(reasoning)
        assert await service.clinical_reasoning_exists(reasoning.id) is True

    async def test_false_for_an_unknown_record(
        self, service: ClinicalReasoningQueryService
    ) -> None:
        assert await service.clinical_reasoning_exists(uuid4()) is False


class TestIsEditable:
    async def test_true_while_pending(
        self, service: ClinicalReasoningQueryService, repo: FakeClinicalReasoningRepository
    ) -> None:
        reasoning = _make_reasoning(ai_generated=True)
        await repo.add(reasoning)
        assert await service.is_editable(reasoning.id) is True

    async def test_true_while_reviewed(
        self, service: ClinicalReasoningQueryService, repo: FakeClinicalReasoningRepository
    ) -> None:
        reasoning = _make_reasoning(ai_generated=False)
        await repo.add(reasoning)
        assert await service.is_editable(reasoning.id) is True

    async def test_false_once_approved(
        self, service: ClinicalReasoningQueryService, repo: FakeClinicalReasoningRepository
    ) -> None:
        reasoning = _make_reasoning()
        reasoning.approve()
        await repo.add(reasoning)
        assert await service.is_editable(reasoning.id) is False

    async def test_false_once_rejected(
        self, service: ClinicalReasoningQueryService, repo: FakeClinicalReasoningRepository
    ) -> None:
        reasoning = _make_reasoning()
        reasoning.reject()
        await repo.add(reasoning)
        assert await service.is_editable(reasoning.id) is False

    async def test_false_for_an_unknown_record(
        self, service: ClinicalReasoningQueryService
    ) -> None:
        assert await service.is_editable(uuid4()) is False


class TestGetClinicalReasoningSummary:
    async def test_returns_summary_for_a_known_record(
        self, service: ClinicalReasoningQueryService, repo: FakeClinicalReasoningRepository
    ) -> None:
        reasoning = _make_reasoning(confidence_score=0.75)
        await repo.add(reasoning)

        summary = await service.get_clinical_reasoning_summary(reasoning.id)

        assert summary is not None
        assert summary.clinical_reasoning_id == reasoning.id
        assert summary.organization_id == reasoning.organization_id
        assert summary.patient_id == reasoning.patient_id
        assert summary.visit_id == reasoning.visit_id
        assert summary.doctor_id == reasoning.doctor_id
        assert summary.confidence_score == 0.75

    async def test_returns_none_for_an_unknown_record(
        self, service: ClinicalReasoningQueryService
    ) -> None:
        assert await service.get_clinical_reasoning_summary(uuid4()) is None


class TestListClinicalReasoningForClinicalNote:
    async def test_returns_records_scoped_to_the_clinical_note(
        self, service: ClinicalReasoningQueryService, repo: FakeClinicalReasoningRepository
    ) -> None:
        clinical_note_id = uuid4()
        await repo.add(_make_reasoning(clinical_note_id=clinical_note_id, reasoning_text="First"))
        await repo.add(_make_reasoning(clinical_note_id=clinical_note_id, reasoning_text="Second"))
        await repo.add(_make_reasoning(reasoning_text="Other note"))

        summaries = await service.list_clinical_reasoning_for_clinical_note(clinical_note_id)

        assert {s.reasoning_text for s in summaries} == {"First", "Second"}

    async def test_returns_empty_list_for_a_clinical_note_without_records(
        self, service: ClinicalReasoningQueryService
    ) -> None:
        assert await service.list_clinical_reasoning_for_clinical_note(uuid4()) == []


class TestListClinicalReasoningForPatient:
    async def test_returns_records_scoped_to_the_patient(
        self, service: ClinicalReasoningQueryService, repo: FakeClinicalReasoningRepository
    ) -> None:
        patient_id = uuid4()
        await repo.add(_make_reasoning(patient_id=patient_id, reasoning_text="A"))
        await repo.add(_make_reasoning(reasoning_text="B"))

        summaries = await service.list_clinical_reasoning_for_patient(patient_id)

        assert [s.reasoning_text for s in summaries] == ["A"]

    async def test_returns_empty_list_for_a_patient_without_records(
        self, service: ClinicalReasoningQueryService
    ) -> None:
        assert await service.list_clinical_reasoning_for_patient(uuid4()) == []
