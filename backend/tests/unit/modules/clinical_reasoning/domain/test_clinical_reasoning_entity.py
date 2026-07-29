"""Unit tests for the `ClinicalReasoning` aggregate's own invariants:
deriving `review_status`/`reviewed_by_doctor` from `ai_generated` at
creation, the Pending -> Reviewed -> Approved/Rejected workflow, and the
"Approved/Rejected becomes immutable" self-check `ensure_editable()`
shares with `update_details()`/`approve()`/`reject()`.
"""

from uuid import uuid4

import pytest

from app.modules.clinical_reasoning.domain.entities import ClinicalReasoning
from app.modules.clinical_reasoning.domain.enums import ReasoningSource, ReviewStatus
from app.modules.clinical_reasoning.domain.events import (
    ClinicalReasoningCreated,
    ClinicalReasoningReviewStatusChanged,
    ClinicalReasoningUpdated,
)
from app.modules.clinical_reasoning.domain.exceptions import (
    ClinicalReasoningNotEditableError,
    ReasoningTextRequiredError,
    ReviewRequiresPendingStatusError,
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


class TestCreate:
    def test_create_sets_identity_fields_and_records_event(self) -> None:
        organization_id = uuid4()
        clinical_note_id = uuid4()
        patient_id = uuid4()
        visit_id = uuid4()
        doctor_id = uuid4()

        reasoning = _make_reasoning(
            organization_id=organization_id,
            clinical_note_id=clinical_note_id,
            patient_id=patient_id,
            visit_id=visit_id,
            doctor_id=doctor_id,
        )

        assert reasoning.organization_id == organization_id
        assert reasoning.clinical_note_id == clinical_note_id
        assert reasoning.patient_id == patient_id
        assert reasoning.visit_id == visit_id
        assert reasoning.doctor_id == doctor_id
        events = reasoning.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ClinicalReasoningCreated)
        assert events[0].clinical_reasoning_id == reasoning.id
        assert events[0].clinical_note_id == clinical_note_id

    def test_ai_generated_starts_pending_and_not_reviewed(self) -> None:
        reasoning = _make_reasoning(ai_generated=True)
        assert reasoning.review_status is ReviewStatus.PENDING
        assert reasoning.reviewed_by_doctor is False

    def test_physician_authored_starts_reviewed_and_reviewed_by_doctor(self) -> None:
        reasoning = _make_reasoning(ai_generated=False, reasoning_source=ReasoningSource.PHYSICIAN)
        assert reasoning.review_status is ReviewStatus.REVIEWED
        assert reasoning.reviewed_by_doctor is True

    def test_blank_reasoning_text_is_rejected(self) -> None:
        with pytest.raises(ReasoningTextRequiredError):
            _make_reasoning(reasoning_text="   ")

    def test_reasoning_text_is_stripped(self) -> None:
        reasoning = _make_reasoning(reasoning_text="  Clear evidence of infection.  ")
        assert reasoning.reasoning_text == "Clear evidence of infection."

    def test_confidence_score_defaults_to_none(self) -> None:
        assert _make_reasoning().confidence_score is None

    def test_confidence_score_is_accepted(self) -> None:
        reasoning = _make_reasoning(confidence_score=0.87)
        assert reasoning.confidence_score == 0.87


class TestUpdateDetails:
    def test_update_changes_fields_and_records_event_while_editable(self) -> None:
        reasoning = _make_reasoning()
        reasoning.pull_events()

        reasoning.update_details(reasoning_text="Revised assessment.", confidence_score=0.5)

        assert reasoning.reasoning_text == "Revised assessment."
        assert reasoning.confidence_score == 0.5
        events = reasoning.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ClinicalReasoningUpdated)

    def test_update_leaves_unspecified_fields_unchanged(self) -> None:
        reasoning = _make_reasoning(confidence_score=0.9)
        reasoning.update_details(reasoning_text="New text")
        assert reasoning.confidence_score == 0.9

    def test_update_with_blank_reasoning_text_raises(self) -> None:
        reasoning = _make_reasoning()
        with pytest.raises(ReasoningTextRequiredError):
            reasoning.update_details(reasoning_text="   ")

    def test_update_once_approved_is_rejected(self) -> None:
        reasoning = _make_reasoning()
        reasoning.approve()
        with pytest.raises(ClinicalReasoningNotEditableError):
            reasoning.update_details(reasoning_text="New text")

    def test_update_once_rejected_is_rejected(self) -> None:
        reasoning = _make_reasoning()
        reasoning.reject()
        with pytest.raises(ClinicalReasoningNotEditableError):
            reasoning.update_details(reasoning_text="New text")

    def test_update_while_reviewed_is_allowed(self) -> None:
        reasoning = _make_reasoning(ai_generated=False)
        reasoning.update_details(reasoning_text="Revised while reviewed")
        assert reasoning.reasoning_text == "Revised while reviewed"


class TestMarkReviewed:
    def test_mark_reviewed_from_pending_sets_status_and_reviewer(self) -> None:
        reasoning = _make_reasoning(ai_generated=True)
        reasoning.pull_events()

        reasoning.mark_reviewed()

        assert reasoning.review_status is ReviewStatus.REVIEWED
        assert reasoning.reviewed_by_doctor is True
        events = reasoning.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ClinicalReasoningReviewStatusChanged)
        assert events[0].review_status == "reviewed"

    def test_mark_reviewed_when_already_reviewed_is_rejected(self) -> None:
        reasoning = _make_reasoning(ai_generated=False)
        with pytest.raises(ReviewRequiresPendingStatusError):
            reasoning.mark_reviewed()

    def test_mark_reviewed_when_approved_is_rejected(self) -> None:
        reasoning = _make_reasoning(ai_generated=True)
        reasoning.approve()
        with pytest.raises(ReviewRequiresPendingStatusError):
            reasoning.mark_reviewed()


class TestApprove:
    def test_approve_from_pending_sets_status_and_reviewer(self) -> None:
        reasoning = _make_reasoning(ai_generated=True)
        reasoning.pull_events()

        reasoning.approve()

        assert reasoning.review_status is ReviewStatus.APPROVED
        assert reasoning.reviewed_by_doctor is True
        events = reasoning.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ClinicalReasoningReviewStatusChanged)
        assert events[0].review_status == "approved"

    def test_approve_from_reviewed_is_accepted(self) -> None:
        reasoning = _make_reasoning(ai_generated=True)
        reasoning.mark_reviewed()
        reasoning.approve()
        assert reasoning.review_status is ReviewStatus.APPROVED

    def test_approve_an_already_approved_record_is_rejected(self) -> None:
        reasoning = _make_reasoning()
        reasoning.approve()
        with pytest.raises(ClinicalReasoningNotEditableError):
            reasoning.approve()

    def test_approve_an_already_rejected_record_is_rejected(self) -> None:
        reasoning = _make_reasoning()
        reasoning.reject()
        with pytest.raises(ClinicalReasoningNotEditableError):
            reasoning.approve()


class TestReject:
    def test_reject_from_pending_sets_status_and_reviewer(self) -> None:
        reasoning = _make_reasoning(ai_generated=True)
        reasoning.pull_events()

        reasoning.reject()

        assert reasoning.review_status is ReviewStatus.REJECTED
        assert reasoning.reviewed_by_doctor is True
        events = reasoning.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ClinicalReasoningReviewStatusChanged)
        assert events[0].review_status == "rejected"

    def test_reject_an_already_rejected_record_is_rejected(self) -> None:
        reasoning = _make_reasoning()
        reasoning.reject()
        with pytest.raises(ClinicalReasoningNotEditableError):
            reasoning.reject()


class TestEnsureEditable:
    def test_does_not_raise_while_pending(self) -> None:
        _make_reasoning(ai_generated=True).ensure_editable()

    def test_does_not_raise_while_reviewed(self) -> None:
        _make_reasoning(ai_generated=False).ensure_editable()

    def test_raises_once_approved(self) -> None:
        reasoning = _make_reasoning()
        reasoning.approve()
        with pytest.raises(ClinicalReasoningNotEditableError):
            reasoning.ensure_editable()

    def test_raises_once_rejected(self) -> None:
        reasoning = _make_reasoning()
        reasoning.reject()
        with pytest.raises(ClinicalReasoningNotEditableError):
            reasoning.ensure_editable()
