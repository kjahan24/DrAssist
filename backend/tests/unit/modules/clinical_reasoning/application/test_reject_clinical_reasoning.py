"""Unit tests for the `RejectClinicalReasoning` use case."""

from uuid import uuid4

import pytest

from app.modules.clinical_reasoning.application.dto import RejectClinicalReasoningInput
from app.modules.clinical_reasoning.application.use_cases.reject_clinical_reasoning import (
    RejectClinicalReasoning,
)
from app.modules.clinical_reasoning.domain.entities import ClinicalReasoning
from app.modules.clinical_reasoning.domain.enums import ReasoningSource, ReviewStatus
from app.modules.clinical_reasoning.domain.exceptions import (
    ClinicalReasoningNotEditableError,
    ClinicalReasoningNotFoundError,
)
from tests.unit.modules.clinical_reasoning.application.fakes import (
    FakeClinicalReasoningRepository,
    FakeUnitOfWork,
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
def reasoning_repository() -> FakeClinicalReasoningRepository:
    return FakeClinicalReasoningRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    reasoning_repository: FakeClinicalReasoningRepository, unit_of_work: FakeUnitOfWork
) -> RejectClinicalReasoning:
    return RejectClinicalReasoning(
        clinical_reasoning_repository=reasoning_repository, unit_of_work=unit_of_work
    )


class TestRejectClinicalReasoning:
    async def test_rejects_a_pending_record(
        self,
        reasoning_repository: FakeClinicalReasoningRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        reasoning = _make_reasoning(ai_generated=True)
        await reasoning_repository.add(reasoning)
        use_case = _use_case(reasoning_repository, unit_of_work)

        output = await use_case.execute(
            RejectClinicalReasoningInput(clinical_reasoning_id=reasoning.id)
        )

        assert output.review_status is ReviewStatus.REJECTED
        stored = await reasoning_repository.get_by_id(reasoning.id)
        assert stored is not None
        assert stored.reviewed_by_doctor is True
        assert unit_of_work.committed is True

    async def test_rejecting_an_already_rejected_record_raises(
        self,
        reasoning_repository: FakeClinicalReasoningRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        reasoning = _make_reasoning()
        reasoning.reject()
        await reasoning_repository.add(reasoning)
        use_case = _use_case(reasoning_repository, unit_of_work)

        with pytest.raises(ClinicalReasoningNotEditableError):
            await use_case.execute(RejectClinicalReasoningInput(clinical_reasoning_id=reasoning.id))

    async def test_unknown_reasoning_record_raises(
        self,
        reasoning_repository: FakeClinicalReasoningRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        use_case = _use_case(reasoning_repository, unit_of_work)

        with pytest.raises(ClinicalReasoningNotFoundError):
            await use_case.execute(RejectClinicalReasoningInput(clinical_reasoning_id=uuid4()))
