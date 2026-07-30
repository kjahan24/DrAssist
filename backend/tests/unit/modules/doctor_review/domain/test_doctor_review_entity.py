"""Unit tests for the `DoctorReview` aggregate's own invariants: always
starting `Pending`, the explicit status-transition map, "reviewed_at
populated exactly once, on the first transition away from Pending", and
the "Approved/Rejected become read-only" self-check `ensure_editable()`
shares with `update_details()`.
"""

from uuid import uuid4

import pytest

from app.modules.doctor_review.domain.entities import DoctorReview
from app.modules.doctor_review.domain.enums import ReviewStatus
from app.modules.doctor_review.domain.events import (
    DoctorReviewCreated,
    DoctorReviewStatusChanged,
    DoctorReviewUpdated,
)
from app.modules.doctor_review.domain.exceptions import (
    DoctorReviewNotEditableError,
    InvalidReviewStatusTransitionError,
)


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


class TestCreate:
    def test_create_sets_identity_fields_and_records_event(self) -> None:
        organization_id = uuid4()
        patient_id = uuid4()
        visit_id = uuid4()
        doctor_id = uuid4()
        clinical_note_id = uuid4()

        review = _make_review(
            organization_id=organization_id,
            patient_id=patient_id,
            visit_id=visit_id,
            doctor_id=doctor_id,
            clinical_note_id=clinical_note_id,
        )

        assert review.organization_id == organization_id
        assert review.patient_id == patient_id
        assert review.visit_id == visit_id
        assert review.doctor_id == doctor_id
        assert review.clinical_note_id == clinical_note_id
        events = review.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DoctorReviewCreated)
        assert events[0].doctor_review_id == review.id
        assert events[0].clinical_note_id == clinical_note_id

    def test_always_starts_pending(self) -> None:
        assert _make_review().review_status is ReviewStatus.PENDING

    def test_reviewed_at_starts_none(self) -> None:
        assert _make_review().reviewed_at is None

    def test_approved_flags_default_to_false(self) -> None:
        review = _make_review()
        assert review.approved_clinical_note is False
        assert review.approved_soap_note is False
        assert review.approved_prescription is False
        assert review.approved_lab_orders is False
        assert review.approved_lab_results is False
        assert review.approved_reasoning is False
        assert review.approved_differential_diagnosis is False
        assert review.approved_icd10 is False

    def test_approved_flags_are_accepted_at_creation(self) -> None:
        review = _make_review(approved_clinical_note=True, approved_soap_note=True)
        assert review.approved_clinical_note is True
        assert review.approved_soap_note is True

    def test_review_comment_defaults_to_none(self) -> None:
        assert _make_review().review_comment is None


class TestUpdateDetails:
    def test_update_changes_fields_and_records_event_while_pending(self) -> None:
        review = _make_review()
        review.pull_events()

        review.update_details(review_comment="Looks complete", approved_soap_note=True)

        assert review.review_comment == "Looks complete"
        assert review.approved_soap_note is True
        events = review.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DoctorReviewUpdated)

    def test_update_leaves_unspecified_fields_unchanged(self) -> None:
        review = _make_review(approved_lab_orders=True)
        review.update_details(review_comment="New comment")
        assert review.approved_lab_orders is True

    def test_update_can_flip_a_flag_back_to_false(self) -> None:
        review = _make_review(approved_soap_note=True)
        review.update_details(approved_soap_note=False)
        assert review.approved_soap_note is False

    def test_update_while_returned_for_revision_is_allowed(self) -> None:
        review = _make_review()
        review.return_for_revision()
        review.update_details(review_comment="Revised")
        assert review.review_comment == "Revised"

    def test_update_once_approved_is_rejected(self) -> None:
        review = _make_review()
        review.approve()
        with pytest.raises(DoctorReviewNotEditableError):
            review.update_details(review_comment="Too late")

    def test_update_once_rejected_is_rejected(self) -> None:
        review = _make_review()
        review.reject()
        with pytest.raises(DoctorReviewNotEditableError):
            review.update_details(review_comment="Too late")


class TestApprove:
    def test_approve_from_pending_sets_status_and_reviewed_at(self) -> None:
        review = _make_review()
        review.pull_events()

        review.approve()

        assert review.review_status is ReviewStatus.APPROVED
        assert review.reviewed_at is not None
        events = review.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DoctorReviewStatusChanged)
        assert events[0].review_status == "approved"

    def test_approve_from_returned_for_revision_is_accepted(self) -> None:
        review = _make_review()
        review.return_for_revision()
        review.approve()
        assert review.review_status is ReviewStatus.APPROVED

    def test_approve_an_already_approved_record_is_rejected(self) -> None:
        review = _make_review()
        review.approve()
        with pytest.raises(InvalidReviewStatusTransitionError):
            review.approve()

    def test_approve_an_already_rejected_record_is_rejected(self) -> None:
        review = _make_review()
        review.reject()
        with pytest.raises(InvalidReviewStatusTransitionError):
            review.approve()


class TestReject:
    def test_reject_from_pending_sets_status_and_reviewed_at(self) -> None:
        review = _make_review()
        review.pull_events()

        review.reject()

        assert review.review_status is ReviewStatus.REJECTED
        assert review.reviewed_at is not None
        events = review.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DoctorReviewStatusChanged)
        assert events[0].review_status == "rejected"

    def test_reject_from_returned_for_revision_is_accepted(self) -> None:
        review = _make_review()
        review.return_for_revision()
        review.reject()
        assert review.review_status is ReviewStatus.REJECTED

    def test_reject_an_already_rejected_record_is_rejected(self) -> None:
        review = _make_review()
        review.reject()
        with pytest.raises(InvalidReviewStatusTransitionError):
            review.reject()


class TestReturnForRevision:
    def test_return_for_revision_from_pending_sets_status_and_reviewed_at(self) -> None:
        review = _make_review()
        review.pull_events()

        review.return_for_revision()

        assert review.review_status is ReviewStatus.RETURNED_FOR_REVISION
        assert review.reviewed_at is not None
        events = review.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DoctorReviewStatusChanged)
        assert events[0].review_status == "returned_for_revision"

    def test_return_for_revision_a_second_time_is_rejected(self) -> None:
        review = _make_review()
        review.return_for_revision()
        with pytest.raises(InvalidReviewStatusTransitionError):
            review.return_for_revision()

    def test_return_for_revision_once_approved_is_rejected(self) -> None:
        review = _make_review()
        review.approve()
        with pytest.raises(InvalidReviewStatusTransitionError):
            review.return_for_revision()

    def test_return_for_revision_once_rejected_is_rejected(self) -> None:
        review = _make_review()
        review.reject()
        with pytest.raises(InvalidReviewStatusTransitionError):
            review.return_for_revision()


class TestReviewedAtIsSetOnce:
    def test_reviewed_at_does_not_change_across_a_second_transition(self) -> None:
        review = _make_review()
        review.return_for_revision()
        first_reviewed_at = review.reviewed_at

        review.approve()

        assert review.reviewed_at == first_reviewed_at


class TestEnsureEditable:
    def test_does_not_raise_while_pending(self) -> None:
        _make_review().ensure_editable()

    def test_does_not_raise_while_returned_for_revision(self) -> None:
        review = _make_review()
        review.return_for_revision()
        review.ensure_editable()

    def test_raises_once_approved(self) -> None:
        review = _make_review()
        review.approve()
        with pytest.raises(DoctorReviewNotEditableError):
            review.ensure_editable()

    def test_raises_once_rejected(self) -> None:
        review = _make_review()
        review.reject()
        with pytest.raises(DoctorReviewNotEditableError):
            review.ensure_editable()
