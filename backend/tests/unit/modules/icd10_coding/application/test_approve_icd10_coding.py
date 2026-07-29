"""Unit tests for the `ApproveICD10Coding` use case ((Pending|Reviewed)
-> Approved)."""

from uuid import uuid4

import pytest

from app.modules.icd10_coding.application.dto import ApproveICD10CodingInput
from app.modules.icd10_coding.application.use_cases.approve_icd10_coding import (
    ApproveICD10Coding,
)
from app.modules.icd10_coding.domain.entities import ICD10Coding
from app.modules.icd10_coding.domain.enums import CodingSource, ReviewStatus
from app.modules.icd10_coding.domain.events import ICD10CodingReviewStatusChanged
from app.modules.icd10_coding.domain.exceptions import (
    ICD10CodingNotEditableError,
    ICD10CodingNotFoundError,
)
from tests.unit.modules.icd10_coding.application.fakes import (
    FakeICD10CodingRepository,
    FakeUnitOfWork,
)


def _make_input(**overrides: object) -> ApproveICD10CodingInput:
    defaults: dict[str, object] = {"icd10_coding_id": uuid4()}
    defaults.update(overrides)
    return ApproveICD10CodingInput(**defaults)  # type: ignore[arg-type]


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
) -> ApproveICD10Coding:
    return ApproveICD10Coding(icd10_coding_repository=coding_repository, unit_of_work=unit_of_work)


class TestApproveICD10Coding:
    async def test_approves_a_pending_code(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        coding = _make_coding(coding_source=CodingSource.AI)
        await coding_repository.add(coding)
        use_case = _use_case(coding_repository, unit_of_work)

        output = await use_case.execute(_make_input(icd10_coding_id=coding.id))

        assert output.review_status is ReviewStatus.APPROVED
        assert any(
            isinstance(e, ICD10CodingReviewStatusChanged) for e in unit_of_work.published_events
        )

    async def test_approves_a_reviewed_code(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        coding = _make_coding(coding_source=CodingSource.PHYSICIAN)
        await coding_repository.add(coding)
        use_case = _use_case(coding_repository, unit_of_work)

        output = await use_case.execute(_make_input(icd10_coding_id=coding.id))

        assert output.review_status is ReviewStatus.APPROVED

    async def test_unknown_coding_raises(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        use_case = _use_case(coding_repository, unit_of_work)

        with pytest.raises(ICD10CodingNotFoundError):
            await use_case.execute(_make_input(icd10_coding_id=uuid4()))

    async def test_approving_an_already_approved_code_raises(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        coding = _make_coding()
        coding.approve()
        await coding_repository.add(coding)
        use_case = _use_case(coding_repository, unit_of_work)

        with pytest.raises(ICD10CodingNotEditableError):
            await use_case.execute(_make_input(icd10_coding_id=coding.id))

    async def test_approving_an_already_rejected_code_raises(
        self, coding_repository: FakeICD10CodingRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        coding = _make_coding()
        coding.reject()
        await coding_repository.add(coding)
        use_case = _use_case(coding_repository, unit_of_work)

        with pytest.raises(ICD10CodingNotEditableError):
            await use_case.execute(_make_input(icd10_coding_id=coding.id))
