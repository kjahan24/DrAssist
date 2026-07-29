"""Unit tests for the `MarkClinicalReasoningReviewed` use case."""

from uuid import uuid4

import pytest

from app.modules.clinical_reasoning.application.dto import MarkClinicalReasoningReviewedInput
from app.modules.clinical_reasoning.application.use_cases.mark_clinical_reasoning_reviewed import (
    MarkClinicalReasoningReviewed,
)
from app.modules.clinical_reasoning.domain.entities import ClinicalReasoning
from app.modules.clinical_reasoning.domain.enums import ReasoningSource, ReviewStatus
from app.modules.clinical_reasoning.domain.exceptions import (
    ClinicalReasoningNotFoundError,
    ReviewRequiresPendingStatusError,
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
) -> MarkClinicalReasoningReviewed:
    return MarkClinicalReasoningReviewed(
        clinical_reasoning_repository=reasoning_repository, unit_of_work=unit_of_work
    )


class TestMarkClinicalReasoningReviewed:
    async def test_marks_a_pending_record_as_reviewed(
        self,
        reasoning_repository: FakeClinicalReasoningRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        reasoning = _make_reasoning(ai_generated=True)
        await reasoning_repository.add(reasoning)
        use_case = _use_case(reasoning_repository, unit_of_work)

        output = await use_case.execute(
            MarkClinicalReasoningReviewedInput(clinical_reasoning_id=reasoning.id)
        )

        assert output.review_status is ReviewStatus.REVIEWED
        assert unit_of_work.committed is True

    async def test_marking_an_already_reviewed_record_raises(
        self,
        reasoning_repository: FakeClinicalReasoningRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        reasoning = _make_reasoning(ai_generated=False)
        await reasoning_repository.add(reasoning)
        use_case = _use_case(reasoning_repository, unit_of_work)

        with pytest.raises(ReviewRequiresPendingStatusError):
            await use_case.execute(
                MarkClinicalReasoningReviewedInput(clinical_reasoning_id=reasoning.id)
            )

    async def test_unknown_reasoning_record_raises(
        self,
        reasoning_repository: FakeClinicalReasoningRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        use_case = _use_case(reasoning_repository, unit_of_work)

        with pytest.raises(ClinicalReasoningNotFoundError):
            await use_case.execute(
                MarkClinicalReasoningReviewedInput(clinical_reasoning_id=uuid4())
            )
