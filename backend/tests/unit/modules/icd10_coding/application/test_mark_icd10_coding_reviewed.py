"""Unit tests for the `MarkICD10CodingReviewed` use case (Pending ->
Reviewed)."""

from uuid import uuid4

import pytest

from app.modules.icd10_coding.application.dto import MarkICD10CodingReviewedInput
from app.modules.icd10_coding.application.use_cases.mark_icd10_coding_reviewed import (
    MarkICD10CodingReviewed,
)
from app.modules.icd10_coding.domain.entities import ICD10Coding
from app.modules.icd10_coding.domain.enums import CodingSource, ReviewStatus
from app.modules.icd10_coding.domain.events import ICD10CodingReviewStatusChanged
from app.modules.icd10_coding.domain.exceptions import (
    ICD10CodingNotFoundError,
    ReviewRequiresPendingStatusError,
)
from tests.unit.modules.icd10_coding.application.fakes import (
    FakeICD10CodingRepository,
    FakeUnitOfWork,
)


def _make_input(**overrides: object) -> MarkICD10CodingReviewedInput:
    defaults: dict[str, object] = {"icd10_coding_id": uuid4()}
    defaults.update(overrides)
    return MarkICD10CodingReviewedInput(**defaults)  # type: ignore[arg-type]


def _make_coding(**overrides: object) -> ICD10Coding:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "clinical_note_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "icd10_code": "J18.9",
        "diagnosis_title": "Pneumonia, unspecified organism",
        "coding_source": CodingSource.AI,
    }
    defaults.update(overrides)
    return ICD10Coding.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def coding_repository() -> FakeICD10CodingRepository:
    return FakeICD10CodingRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
) -> MarkICD10CodingReviewed:
    return MarkICD10CodingReviewed(
        icd10_coding_repository=coding_repository, unit_of_work=unit_of_work
    )


class TestMarkICD10CodingReviewed:
    async def test_marks_a_pending_code_as_reviewed(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        coding = _make_coding(coding_source=CodingSource.AI)
        await coding_repository.add(coding)
        use_case = _use_case(coding_repository, unit_of_work)

        output = await use_case.execute(_make_input(icd10_coding_id=coding.id))

        assert output.review_status is ReviewStatus.REVIEWED
        assert any(
            isinstance(e, ICD10CodingReviewStatusChanged) for e in unit_of_work.published_events
        )

    async def test_unknown_coding_raises(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        use_case = _use_case(coding_repository, unit_of_work)

        with pytest.raises(ICD10CodingNotFoundError):
            await use_case.execute(_make_input(icd10_coding_id=uuid4()))

    async def test_marking_an_already_reviewed_code_raises(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        coding = _make_coding(coding_source=CodingSource.PHYSICIAN)
        await coding_repository.add(coding)
        use_case = _use_case(coding_repository, unit_of_work)

        with pytest.raises(ReviewRequiresPendingStatusError):
            await use_case.execute(_make_input(icd10_coding_id=coding.id))
