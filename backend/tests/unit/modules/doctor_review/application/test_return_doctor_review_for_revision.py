"""Unit tests for the `ReturnDoctorReviewForRevision` use case
(Pending -> ReturnedForRevision)."""

from uuid import uuid4

import pytest

from app.modules.doctor_review.application.dto import ReturnDoctorReviewForRevisionInput
from app.modules.doctor_review.application.use_cases.return_doctor_review_for_revision import (
    ReturnDoctorReviewForRevision,
)
from app.modules.doctor_review.domain.entities import DoctorReview
from app.modules.doctor_review.domain.enums import ReviewStatus
from app.modules.doctor_review.domain.events import DoctorReviewStatusChanged
from app.modules.doctor_review.domain.exceptions import (
    DoctorReviewNotFoundError,
    InvalidReviewStatusTransitionError,
)
from tests.unit.modules.doctor_review.application.fakes import (
    FakeDoctorReviewRepository,
    FakeUnitOfWork,
)


def _make_input(**overrides: object) -> ReturnDoctorReviewForRevisionInput:
    defaults: dict[str, object] = {"doctor_review_id": uuid4()}
    defaults.update(overrides)
    return ReturnDoctorReviewForRevisionInput(**defaults)  # type: ignore[arg-type]


def _make_review(**overrides: object) -> DoctorReview:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "clinical_note_id": uuid4(),
    }
    defaults.update(overrides)
    return DoctorReview.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def review_repository() -> FakeDoctorReviewRepository:
    return FakeDoctorReviewRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    review_repository: FakeDoctorReviewRepository, unit_of_work: FakeUnitOfWork
) -> ReturnDoctorReviewForRevision:
    return ReturnDoctorReviewForRevision(
        doctor_review_repository=review_repository, unit_of_work=unit_of_work
    )


class TestReturnDoctorReviewForRevision:
    async def test_returns_a_pending_review_for_revision(
        self, review_repository: FakeDoctorReviewRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        review = _make_review()
        await review_repository.add(review)
        use_case = _use_case(review_repository, unit_of_work)

        output = await use_case.execute(_make_input(doctor_review_id=review.id))

        assert output.review_status is ReviewStatus.RETURNED_FOR_REVISION
        assert output.reviewed_at is not None
        assert any(isinstance(e, DoctorReviewStatusChanged) for e in unit_of_work.published_events)

    async def test_unknown_review_raises(
        self, review_repository: FakeDoctorReviewRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        use_case = _use_case(review_repository, unit_of_work)

        with pytest.raises(DoctorReviewNotFoundError):
            await use_case.execute(_make_input(doctor_review_id=uuid4()))

    async def test_returning_an_already_returned_review_raises(
        self, review_repository: FakeDoctorReviewRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        review = _make_review()
        review.return_for_revision()
        await review_repository.add(review)
        use_case = _use_case(review_repository, unit_of_work)

        with pytest.raises(InvalidReviewStatusTransitionError):
            await use_case.execute(_make_input(doctor_review_id=review.id))

    async def test_returning_an_approved_review_raises(
        self, review_repository: FakeDoctorReviewRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        review = _make_review()
        review.approve()
        await review_repository.add(review)
        use_case = _use_case(review_repository, unit_of_work)

        with pytest.raises(InvalidReviewStatusTransitionError):
            await use_case.execute(_make_input(doctor_review_id=review.id))
