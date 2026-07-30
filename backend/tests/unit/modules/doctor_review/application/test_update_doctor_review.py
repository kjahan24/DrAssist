"""Unit tests for the `UpdateDoctorReview` use case. Re-validates the
*effective* `approved_*` values (input if provided, else the review's
current value) through `DoctorReviewConsistencyService` on every call."""

from uuid import uuid4

import pytest

from app.modules.doctor_review.application.dto import UpdateDoctorReviewInput
from app.modules.doctor_review.application.services.doctor_review_consistency_service import (
    DoctorReviewConsistencyService,
)
from app.modules.doctor_review.application.use_cases.update_doctor_review import (
    UpdateDoctorReview,
)
from app.modules.doctor_review.domain.entities import DoctorReview
from app.modules.doctor_review.domain.events import DoctorReviewUpdated
from app.modules.doctor_review.domain.exceptions import (
    ApprovedCategoryMissingRecordError,
    DoctorReviewNotEditableError,
    DoctorReviewNotFoundError,
)
from tests.unit.modules.doctor_review.application.fakes import (
    FakeClinicalReasoningQueryPort,
    FakeDifferentialDiagnosisQueryPort,
    FakeDoctorReviewRepository,
    FakeICD10CodingQueryPort,
    FakeLabOrderQueryPort,
    FakeLabResultQueryPort,
    FakePrescriptionQueryPort,
    FakeSOAPNoteQueryPort,
    FakeUnitOfWork,
)


def _make_input(**overrides: object) -> UpdateDoctorReviewInput:
    defaults: dict[str, object] = {"doctor_review_id": uuid4()}
    defaults.update(overrides)
    return UpdateDoctorReviewInput(**defaults)  # type: ignore[arg-type]


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


def _consistency_service(
    *, soap_note_query_port: FakeSOAPNoteQueryPort | None = None
) -> DoctorReviewConsistencyService:
    return DoctorReviewConsistencyService(
        soap_note_query_port=soap_note_query_port or FakeSOAPNoteQueryPort(),
        prescription_query_port=FakePrescriptionQueryPort(),
        lab_order_query_port=FakeLabOrderQueryPort(),
        lab_result_query_port=FakeLabResultQueryPort(),
        clinical_reasoning_query_port=FakeClinicalReasoningQueryPort(),
        differential_diagnosis_query_port=FakeDifferentialDiagnosisQueryPort(),
        icd10_coding_query_port=FakeICD10CodingQueryPort(),
    )


@pytest.fixture
def review_repository() -> FakeDoctorReviewRepository:
    return FakeDoctorReviewRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    review_repository: FakeDoctorReviewRepository,
    unit_of_work: FakeUnitOfWork,
    consistency_service: DoctorReviewConsistencyService | None = None,
) -> UpdateDoctorReview:
    return UpdateDoctorReview(
        doctor_review_repository=review_repository,
        consistency_service=consistency_service or _consistency_service(),
        unit_of_work=unit_of_work,
    )


class TestUpdateDoctorReview:
    async def test_updates_review_comment_while_pending(
        self, review_repository: FakeDoctorReviewRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        review = _make_review()
        await review_repository.add(review)
        use_case = _use_case(review_repository, unit_of_work)

        output = await use_case.execute(
            _make_input(doctor_review_id=review.id, review_comment="Looks good")
        )

        stored = await review_repository.get_by_id(output.doctor_review_id)
        assert stored is not None
        assert stored.review_comment == "Looks good"
        assert unit_of_work.committed is True
        assert any(isinstance(e, DoctorReviewUpdated) for e in unit_of_work.published_events)

    async def test_unknown_review_raises(
        self, review_repository: FakeDoctorReviewRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        use_case = _use_case(review_repository, unit_of_work)

        with pytest.raises(DoctorReviewNotFoundError):
            await use_case.execute(_make_input(doctor_review_id=uuid4()))

    async def test_updating_an_approved_review_raises(
        self, review_repository: FakeDoctorReviewRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        review = _make_review()
        review.approve()
        await review_repository.add(review)
        use_case = _use_case(review_repository, unit_of_work)

        with pytest.raises(DoctorReviewNotEditableError):
            await use_case.execute(
                _make_input(doctor_review_id=review.id, review_comment="Too late")
            )

    async def test_updating_a_rejected_review_raises(
        self, review_repository: FakeDoctorReviewRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        review = _make_review()
        review.reject()
        await review_repository.add(review)
        use_case = _use_case(review_repository, unit_of_work)

        with pytest.raises(DoctorReviewNotEditableError):
            await use_case.execute(
                _make_input(doctor_review_id=review.id, review_comment="Too late")
            )

    async def test_updating_a_returned_for_revision_review_is_allowed(
        self, review_repository: FakeDoctorReviewRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        review = _make_review()
        review.return_for_revision()
        await review_repository.add(review)
        use_case = _use_case(review_repository, unit_of_work)

        output = await use_case.execute(
            _make_input(doctor_review_id=review.id, review_comment="Revised")
        )

        stored = await review_repository.get_by_id(output.doctor_review_id)
        assert stored is not None
        assert stored.review_comment == "Revised"

    async def test_flipping_a_category_to_true_without_backing_record_raises(
        self, review_repository: FakeDoctorReviewRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        review = _make_review()
        await review_repository.add(review)
        use_case = _use_case(review_repository, unit_of_work)

        with pytest.raises(ApprovedCategoryMissingRecordError):
            await use_case.execute(_make_input(doctor_review_id=review.id, approved_soap_note=True))

    async def test_leaving_an_already_true_category_unspecified_is_revalidated(
        self, review_repository: FakeDoctorReviewRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        review = _make_review(clinical_note_id=clinical_note_id, approved_soap_note=True)
        await review_repository.add(review)
        consistency_service = _consistency_service(soap_note_query_port=FakeSOAPNoteQueryPort())
        use_case = _use_case(review_repository, unit_of_work, consistency_service)

        with pytest.raises(ApprovedCategoryMissingRecordError):
            await use_case.execute(
                _make_input(doctor_review_id=review.id, review_comment="unchanged flags")
            )

    async def test_flipping_a_category_back_to_false_needs_no_backing_record(
        self, review_repository: FakeDoctorReviewRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        review = _make_review(approved_soap_note=True)
        await review_repository.add(review)
        use_case = _use_case(review_repository, unit_of_work)

        output = await use_case.execute(
            _make_input(doctor_review_id=review.id, approved_soap_note=False)
        )

        stored = await review_repository.get_by_id(output.doctor_review_id)
        assert stored is not None
        assert stored.approved_soap_note is False
