"""Unit tests for the `ICD10Coding` aggregate's own invariants: deriving
`review_status` from `coding_source` at creation, uppercase normalization
of `icd10_code`, the mutable `primary_code` transitions, the Pending ->
Reviewed -> Approved/Rejected workflow, and the "Approved and Rejected
become read-only" self-check `ensure_editable()` shares with
`update_details()`/`mark_as_primary()`/`unmark_as_primary()`/`approve()`/
`reject()`.
"""

from uuid import uuid4

import pytest

from app.modules.icd10_coding.domain.entities import ICD10Coding
from app.modules.icd10_coding.domain.enums import CodingSource, ReviewStatus
from app.modules.icd10_coding.domain.events import (
    ICD10CodingCreated,
    ICD10CodingPrimaryChanged,
    ICD10CodingReviewStatusChanged,
    ICD10CodingUpdated,
)
from app.modules.icd10_coding.domain.exceptions import (
    DiagnosisTitleRequiredError,
    ICD10CodeRequiredError,
    ICD10CodingNotEditableError,
    ReviewRequiresPendingStatusError,
)


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


class TestCreate:
    def test_create_sets_identity_fields_and_records_event(self) -> None:
        organization_id = uuid4()
        clinical_note_id = uuid4()
        patient_id = uuid4()
        visit_id = uuid4()
        doctor_id = uuid4()

        coding = _make_coding(
            organization_id=organization_id,
            clinical_note_id=clinical_note_id,
            patient_id=patient_id,
            visit_id=visit_id,
            doctor_id=doctor_id,
        )

        assert coding.organization_id == organization_id
        assert coding.clinical_note_id == clinical_note_id
        assert coding.patient_id == patient_id
        assert coding.visit_id == visit_id
        assert coding.doctor_id == doctor_id
        events = coding.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ICD10CodingCreated)
        assert events[0].icd10_coding_id == coding.id
        assert events[0].clinical_note_id == clinical_note_id

    def test_ai_generated_starts_pending(self) -> None:
        coding = _make_coding(coding_source=CodingSource.AI)
        assert coding.review_status is ReviewStatus.PENDING

    def test_hybrid_starts_pending(self) -> None:
        coding = _make_coding(coding_source=CodingSource.HYBRID)
        assert coding.review_status is ReviewStatus.PENDING

    def test_physician_generated_starts_reviewed(self) -> None:
        coding = _make_coding(coding_source=CodingSource.PHYSICIAN)
        assert coding.review_status is ReviewStatus.REVIEWED

    def test_blank_icd10_code_is_rejected(self) -> None:
        with pytest.raises(ICD10CodeRequiredError):
            _make_coding(icd10_code="   ")

    def test_icd10_code_is_stripped_and_uppercased(self) -> None:
        coding = _make_coding(icd10_code="  j18.9  ")
        assert coding.icd10_code == "J18.9"

    def test_blank_diagnosis_title_is_rejected(self) -> None:
        with pytest.raises(DiagnosisTitleRequiredError):
            _make_coding(diagnosis_title="   ")

    def test_diagnosis_title_is_stripped(self) -> None:
        coding = _make_coding(diagnosis_title="  Pneumonia  ")
        assert coding.diagnosis_title == "Pneumonia"

    def test_primary_code_defaults_to_false(self) -> None:
        assert _make_coding().primary_code is False

    def test_differential_diagnosis_id_defaults_to_none(self) -> None:
        assert _make_coding().differential_diagnosis_id is None

    def test_differential_diagnosis_id_is_accepted(self) -> None:
        differential_diagnosis_id = uuid4()
        coding = _make_coding(differential_diagnosis_id=differential_diagnosis_id)
        assert coding.differential_diagnosis_id == differential_diagnosis_id


class TestUpdateDetails:
    def test_update_changes_fields_and_records_event_while_editable(self) -> None:
        coding = _make_coding()
        coding.pull_events()

        coding.update_details(
            diagnosis_title="Bacterial pneumonia", coding_notes="Confirmed via chest X-ray"
        )

        assert coding.diagnosis_title == "Bacterial pneumonia"
        assert coding.coding_notes == "Confirmed via chest X-ray"
        events = coding.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ICD10CodingUpdated)

    def test_update_leaves_unspecified_fields_unchanged(self) -> None:
        coding = _make_coding(coding_notes="Original note")
        coding.update_details(diagnosis_title="New title")
        assert coding.coding_notes == "Original note"

    def test_update_with_blank_diagnosis_title_raises(self) -> None:
        coding = _make_coding()
        with pytest.raises(DiagnosisTitleRequiredError):
            coding.update_details(diagnosis_title="   ")

    def test_update_once_approved_is_rejected(self) -> None:
        coding = _make_coding()
        coding.approve()
        with pytest.raises(ICD10CodingNotEditableError):
            coding.update_details(diagnosis_title="New title")

    def test_update_once_rejected_is_rejected(self) -> None:
        coding = _make_coding()
        coding.reject()
        with pytest.raises(ICD10CodingNotEditableError):
            coding.update_details(diagnosis_title="New title")

    def test_update_while_reviewed_is_allowed(self) -> None:
        coding = _make_coding(coding_source=CodingSource.PHYSICIAN)
        coding.update_details(diagnosis_title="Revised while reviewed")
        assert coding.diagnosis_title == "Revised while reviewed"


class TestMarkAsPrimary:
    def test_mark_as_primary_sets_flag_and_records_event(self) -> None:
        coding = _make_coding()
        coding.pull_events()

        coding.mark_as_primary()

        assert coding.primary_code is True
        events = coding.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ICD10CodingPrimaryChanged)
        assert events[0].primary_code is True

    def test_mark_as_primary_when_already_primary_is_idempotent_and_records_no_event(self) -> None:
        coding = _make_coding(primary_code=True)
        coding.pull_events()

        coding.mark_as_primary()

        assert coding.primary_code is True
        assert coding.pull_events() == []

    def test_mark_as_primary_once_approved_is_rejected(self) -> None:
        coding = _make_coding()
        coding.approve()
        with pytest.raises(ICD10CodingNotEditableError):
            coding.mark_as_primary()

    def test_mark_as_primary_once_rejected_is_rejected(self) -> None:
        coding = _make_coding()
        coding.reject()
        with pytest.raises(ICD10CodingNotEditableError):
            coding.mark_as_primary()


class TestUnmarkAsPrimary:
    def test_unmark_as_primary_clears_flag_and_records_event(self) -> None:
        coding = _make_coding(primary_code=True)
        coding.pull_events()

        coding.unmark_as_primary()

        assert coding.primary_code is False
        events = coding.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ICD10CodingPrimaryChanged)
        assert events[0].primary_code is False

    def test_unmark_as_primary_when_already_not_primary_records_no_event(self) -> None:
        coding = _make_coding(primary_code=False)
        coding.pull_events()

        coding.unmark_as_primary()

        assert coding.pull_events() == []

    def test_unmark_as_primary_once_approved_is_rejected(self) -> None:
        coding = _make_coding(primary_code=True)
        coding.approve()
        with pytest.raises(ICD10CodingNotEditableError):
            coding.unmark_as_primary()


class TestMarkReviewed:
    def test_mark_reviewed_from_pending_sets_status(self) -> None:
        coding = _make_coding(coding_source=CodingSource.AI)
        coding.pull_events()

        coding.mark_reviewed()

        assert coding.review_status is ReviewStatus.REVIEWED
        events = coding.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ICD10CodingReviewStatusChanged)
        assert events[0].review_status == "reviewed"

    def test_mark_reviewed_when_already_reviewed_is_rejected(self) -> None:
        coding = _make_coding(coding_source=CodingSource.PHYSICIAN)
        with pytest.raises(ReviewRequiresPendingStatusError):
            coding.mark_reviewed()

    def test_mark_reviewed_when_approved_is_rejected(self) -> None:
        coding = _make_coding(coding_source=CodingSource.AI)
        coding.approve()
        with pytest.raises(ReviewRequiresPendingStatusError):
            coding.mark_reviewed()


class TestApprove:
    def test_approve_from_pending_sets_status(self) -> None:
        coding = _make_coding(coding_source=CodingSource.AI)
        coding.pull_events()

        coding.approve()

        assert coding.review_status is ReviewStatus.APPROVED
        events = coding.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ICD10CodingReviewStatusChanged)
        assert events[0].review_status == "approved"

    def test_approve_from_reviewed_is_accepted(self) -> None:
        coding = _make_coding(coding_source=CodingSource.AI)
        coding.mark_reviewed()
        coding.approve()
        assert coding.review_status is ReviewStatus.APPROVED

    def test_approve_an_already_approved_record_is_rejected(self) -> None:
        coding = _make_coding()
        coding.approve()
        with pytest.raises(ICD10CodingNotEditableError):
            coding.approve()

    def test_approve_an_already_rejected_record_is_rejected(self) -> None:
        coding = _make_coding()
        coding.reject()
        with pytest.raises(ICD10CodingNotEditableError):
            coding.approve()


class TestReject:
    def test_reject_from_pending_sets_status(self) -> None:
        coding = _make_coding(coding_source=CodingSource.AI)
        coding.pull_events()

        coding.reject()

        assert coding.review_status is ReviewStatus.REJECTED
        events = coding.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ICD10CodingReviewStatusChanged)
        assert events[0].review_status == "rejected"

    def test_reject_an_already_rejected_record_is_rejected(self) -> None:
        coding = _make_coding()
        coding.reject()
        with pytest.raises(ICD10CodingNotEditableError):
            coding.reject()


class TestEnsureEditable:
    def test_does_not_raise_while_pending(self) -> None:
        _make_coding(coding_source=CodingSource.AI).ensure_editable()

    def test_does_not_raise_while_reviewed(self) -> None:
        _make_coding(coding_source=CodingSource.PHYSICIAN).ensure_editable()

    def test_raises_once_approved(self) -> None:
        coding = _make_coding()
        coding.approve()
        with pytest.raises(ICD10CodingNotEditableError):
            coding.ensure_editable()

    def test_raises_once_rejected(self) -> None:
        coding = _make_coding()
        coding.reject()
        with pytest.raises(ICD10CodingNotEditableError):
            coding.ensure_editable()
