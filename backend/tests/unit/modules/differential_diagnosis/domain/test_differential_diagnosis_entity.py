"""Unit tests for the `DifferentialDiagnosis` aggregate's own invariants:
deriving `review_status` from `diagnosis_source` at creation, the
Pending -> Reviewed -> Approved/Rejected workflow, and the "Approved and
Rejected become read-only" self-check `ensure_editable()` shares with
`update_details()`/`approve()`/`reject()`.
"""

from uuid import uuid4

import pytest

from app.modules.differential_diagnosis.domain.entities import DifferentialDiagnosis
from app.modules.differential_diagnosis.domain.enums import DiagnosisSource, ReviewStatus
from app.modules.differential_diagnosis.domain.events import (
    DifferentialDiagnosisCreated,
    DifferentialDiagnosisReviewStatusChanged,
    DifferentialDiagnosisUpdated,
)
from app.modules.differential_diagnosis.domain.exceptions import (
    DiagnosisNameRequiredError,
    DifferentialDiagnosisNotEditableError,
    InvalidRankingError,
    ReviewRequiresPendingStatusError,
)


def _make_diagnosis(**overrides: object) -> DifferentialDiagnosis:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "clinical_note_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "diagnosis_name": "Community-acquired pneumonia",
        "diagnosis_source": DiagnosisSource.AI,
        "ranking": 1,
    }
    defaults.update(overrides)
    return DifferentialDiagnosis.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_sets_identity_fields_and_records_event(self) -> None:
        organization_id = uuid4()
        clinical_note_id = uuid4()
        patient_id = uuid4()
        visit_id = uuid4()
        doctor_id = uuid4()

        diagnosis = _make_diagnosis(
            organization_id=organization_id,
            clinical_note_id=clinical_note_id,
            patient_id=patient_id,
            visit_id=visit_id,
            doctor_id=doctor_id,
        )

        assert diagnosis.organization_id == organization_id
        assert diagnosis.clinical_note_id == clinical_note_id
        assert diagnosis.patient_id == patient_id
        assert diagnosis.visit_id == visit_id
        assert diagnosis.doctor_id == doctor_id
        events = diagnosis.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DifferentialDiagnosisCreated)
        assert events[0].differential_diagnosis_id == diagnosis.id
        assert events[0].clinical_note_id == clinical_note_id

    def test_ai_generated_starts_pending(self) -> None:
        diagnosis = _make_diagnosis(diagnosis_source=DiagnosisSource.AI)
        assert diagnosis.review_status is ReviewStatus.PENDING

    def test_hybrid_starts_pending(self) -> None:
        diagnosis = _make_diagnosis(diagnosis_source=DiagnosisSource.HYBRID)
        assert diagnosis.review_status is ReviewStatus.PENDING

    def test_physician_authored_starts_reviewed(self) -> None:
        diagnosis = _make_diagnosis(diagnosis_source=DiagnosisSource.PHYSICIAN)
        assert diagnosis.review_status is ReviewStatus.REVIEWED

    def test_blank_diagnosis_name_is_rejected(self) -> None:
        with pytest.raises(DiagnosisNameRequiredError):
            _make_diagnosis(diagnosis_name="   ")

    def test_diagnosis_name_is_stripped(self) -> None:
        diagnosis = _make_diagnosis(diagnosis_name="  Pneumonia  ")
        assert diagnosis.diagnosis_name == "Pneumonia"

    def test_ranking_below_one_is_rejected(self) -> None:
        with pytest.raises(InvalidRankingError):
            _make_diagnosis(ranking=0)

    def test_excluded_defaults_to_false(self) -> None:
        assert _make_diagnosis().excluded is False

    def test_clinical_reasoning_id_defaults_to_none(self) -> None:
        assert _make_diagnosis().clinical_reasoning_id is None

    def test_clinical_reasoning_id_is_accepted(self) -> None:
        clinical_reasoning_id = uuid4()
        diagnosis = _make_diagnosis(clinical_reasoning_id=clinical_reasoning_id)
        assert diagnosis.clinical_reasoning_id == clinical_reasoning_id


class TestUpdateDetails:
    def test_update_changes_fields_and_records_event_while_editable(self) -> None:
        diagnosis = _make_diagnosis()
        diagnosis.pull_events()

        diagnosis.update_details(
            diagnosis_name="Atypical pneumonia",
            likelihood_score=0.6,
            supporting_evidence="Crackles on auscultation",
            excluded=True,
        )

        assert diagnosis.diagnosis_name == "Atypical pneumonia"
        assert diagnosis.likelihood_score == 0.6
        assert diagnosis.supporting_evidence == "Crackles on auscultation"
        assert diagnosis.excluded is True
        events = diagnosis.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DifferentialDiagnosisUpdated)

    def test_update_leaves_unspecified_fields_unchanged(self) -> None:
        diagnosis = _make_diagnosis(likelihood_score=0.9)
        diagnosis.update_details(diagnosis_name="New name")
        assert diagnosis.likelihood_score == 0.9

    def test_update_with_blank_diagnosis_name_raises(self) -> None:
        diagnosis = _make_diagnosis()
        with pytest.raises(DiagnosisNameRequiredError):
            diagnosis.update_details(diagnosis_name="   ")

    def test_update_once_approved_is_rejected(self) -> None:
        diagnosis = _make_diagnosis()
        diagnosis.approve()
        with pytest.raises(DifferentialDiagnosisNotEditableError):
            diagnosis.update_details(diagnosis_name="New name")

    def test_update_once_rejected_is_rejected(self) -> None:
        diagnosis = _make_diagnosis()
        diagnosis.reject()
        with pytest.raises(DifferentialDiagnosisNotEditableError):
            diagnosis.update_details(diagnosis_name="New name")

    def test_update_while_reviewed_is_allowed(self) -> None:
        diagnosis = _make_diagnosis(diagnosis_source=DiagnosisSource.PHYSICIAN)
        diagnosis.update_details(diagnosis_name="Revised while reviewed")
        assert diagnosis.diagnosis_name == "Revised while reviewed"


class TestMarkReviewed:
    def test_mark_reviewed_from_pending_sets_status(self) -> None:
        diagnosis = _make_diagnosis(diagnosis_source=DiagnosisSource.AI)
        diagnosis.pull_events()

        diagnosis.mark_reviewed()

        assert diagnosis.review_status is ReviewStatus.REVIEWED
        events = diagnosis.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DifferentialDiagnosisReviewStatusChanged)
        assert events[0].review_status == "reviewed"

    def test_mark_reviewed_when_already_reviewed_is_rejected(self) -> None:
        diagnosis = _make_diagnosis(diagnosis_source=DiagnosisSource.PHYSICIAN)
        with pytest.raises(ReviewRequiresPendingStatusError):
            diagnosis.mark_reviewed()

    def test_mark_reviewed_when_approved_is_rejected(self) -> None:
        diagnosis = _make_diagnosis(diagnosis_source=DiagnosisSource.AI)
        diagnosis.approve()
        with pytest.raises(ReviewRequiresPendingStatusError):
            diagnosis.mark_reviewed()


class TestApprove:
    def test_approve_from_pending_sets_status(self) -> None:
        diagnosis = _make_diagnosis(diagnosis_source=DiagnosisSource.AI)
        diagnosis.pull_events()

        diagnosis.approve()

        assert diagnosis.review_status is ReviewStatus.APPROVED
        events = diagnosis.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DifferentialDiagnosisReviewStatusChanged)
        assert events[0].review_status == "approved"

    def test_approve_from_reviewed_is_accepted(self) -> None:
        diagnosis = _make_diagnosis(diagnosis_source=DiagnosisSource.AI)
        diagnosis.mark_reviewed()
        diagnosis.approve()
        assert diagnosis.review_status is ReviewStatus.APPROVED

    def test_approve_an_already_approved_record_is_rejected(self) -> None:
        diagnosis = _make_diagnosis()
        diagnosis.approve()
        with pytest.raises(DifferentialDiagnosisNotEditableError):
            diagnosis.approve()

    def test_approve_an_already_rejected_record_is_rejected(self) -> None:
        diagnosis = _make_diagnosis()
        diagnosis.reject()
        with pytest.raises(DifferentialDiagnosisNotEditableError):
            diagnosis.approve()


class TestReject:
    def test_reject_from_pending_sets_status(self) -> None:
        diagnosis = _make_diagnosis(diagnosis_source=DiagnosisSource.AI)
        diagnosis.pull_events()

        diagnosis.reject()

        assert diagnosis.review_status is ReviewStatus.REJECTED
        events = diagnosis.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DifferentialDiagnosisReviewStatusChanged)
        assert events[0].review_status == "rejected"

    def test_reject_an_already_rejected_record_is_rejected(self) -> None:
        diagnosis = _make_diagnosis()
        diagnosis.reject()
        with pytest.raises(DifferentialDiagnosisNotEditableError):
            diagnosis.reject()


class TestEnsureEditable:
    def test_does_not_raise_while_pending(self) -> None:
        _make_diagnosis(diagnosis_source=DiagnosisSource.AI).ensure_editable()

    def test_does_not_raise_while_reviewed(self) -> None:
        _make_diagnosis(diagnosis_source=DiagnosisSource.PHYSICIAN).ensure_editable()

    def test_raises_once_approved(self) -> None:
        diagnosis = _make_diagnosis()
        diagnosis.approve()
        with pytest.raises(DifferentialDiagnosisNotEditableError):
            diagnosis.ensure_editable()

    def test_raises_once_rejected(self) -> None:
        diagnosis = _make_diagnosis()
        diagnosis.reject()
        with pytest.raises(DifferentialDiagnosisNotEditableError):
            diagnosis.ensure_editable()
