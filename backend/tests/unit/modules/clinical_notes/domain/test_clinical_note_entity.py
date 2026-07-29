"""Unit tests for the `ClinicalNote` aggregate's invariants, including
its Draft -> In Review -> Signed -> Locked workflow."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.modules.clinical_notes.domain.entities import ClinicalNote
from app.modules.clinical_notes.domain.enums import ClinicalNoteStatus, ClinicalNoteType
from app.modules.clinical_notes.domain.events import (
    ClinicalNoteCreated,
    ClinicalNoteStatusChanged,
    ClinicalNoteUpdated,
)
from app.modules.clinical_notes.domain.exceptions import (
    ClinicalNoteNotEditableError,
    LockedAtNotAllowedError,
    LockedAtRequiredError,
    LockRequiresSignedNoteError,
    NoteNumberRequiredError,
    SignatureNotAllowedError,
    SignatureRequiredError,
)
from app.modules.clinical_notes.domain.value_objects import Signature


def _make_note(**overrides: object) -> ClinicalNote:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "note_number": "CN-0001",
        "note_type": ClinicalNoteType.INITIAL,
        "encounter_datetime": datetime(2026, 1, 1, 9, 0),
    }
    defaults.update(overrides)
    return ClinicalNote.create(**defaults)  # type: ignore[arg-type]


def _make_raw_note(**overrides: object) -> ClinicalNote:
    """Bypasses `create()` to exercise `__post_init__` directly with an
    arbitrary status/signature/locked_at combination, the same
    "construct the dataclass directly" pattern used across this
    codebase's other entity tests to reach validation that a well-formed
    `create()` call could never trigger."""
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "note_number": "CN-0001",
        "note_type": ClinicalNoteType.INITIAL,
        "encounter_datetime": datetime(2026, 1, 1, 9, 0),
    }
    defaults.update(overrides)
    return ClinicalNote(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_records_clinical_note_created_event(self) -> None:
        organization_id = uuid4()
        patient_id = uuid4()
        visit_id = uuid4()
        note = _make_note(organization_id=organization_id, patient_id=patient_id, visit_id=visit_id)

        assert note.organization_id == organization_id
        assert note.patient_id == patient_id
        assert note.visit_id == visit_id
        events = note.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ClinicalNoteCreated)

    def test_blank_note_number_is_rejected(self) -> None:
        with pytest.raises(NoteNumberRequiredError):
            _make_note(note_number="   ")

    def test_note_number_is_stripped(self) -> None:
        note = _make_note(note_number="  CN-0002  ")
        assert note.note_number == "CN-0002"

    def test_default_status_is_draft(self) -> None:
        note = _make_note()
        assert note.status is ClinicalNoteStatus.DRAFT

    def test_default_signature_is_none(self) -> None:
        note = _make_note()
        assert note.signature is None

    def test_default_locked_at_is_none(self) -> None:
        note = _make_note()
        assert note.locked_at is None

    def test_default_ai_generated_is_false(self) -> None:
        note = _make_note()
        assert note.ai_generated is False


class TestUpdateDetails:
    def test_update_changes_fields_and_records_event_while_draft(self) -> None:
        note = _make_note()
        note.pull_events()

        note.update_details(plan_summary="Continue current medication")

        assert note.plan_summary == "Continue current medication"
        events = note.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ClinicalNoteUpdated)

    def test_update_leaves_unspecified_fields_unchanged(self) -> None:
        note = _make_note(assessment_summary="Stable")
        note.update_details(plan_summary="Follow up in 2 weeks")
        assert note.assessment_summary == "Stable"

    def test_update_while_in_review_is_rejected(self) -> None:
        note = _make_note()
        note.submit_for_review()
        with pytest.raises(ClinicalNoteNotEditableError):
            note.update_details(plan_summary="New plan")

    def test_update_while_signed_is_rejected(self) -> None:
        note = _make_note()
        note.sign(signed_at=datetime(2026, 1, 1, 10, 0), signed_by=uuid4())
        with pytest.raises(ClinicalNoteNotEditableError):
            note.update_details(plan_summary="New plan")

    def test_update_while_locked_is_rejected(self) -> None:
        note = _make_note()
        note.sign(signed_at=datetime(2026, 1, 1, 10, 0), signed_by=uuid4())
        note.lock(locked_at=datetime(2026, 1, 1, 11, 0))
        with pytest.raises(ClinicalNoteNotEditableError):
            note.update_details(plan_summary="New plan")


class TestSubmitForReview:
    def test_submit_for_review_sets_status_and_records_event(self) -> None:
        note = _make_note()
        note.pull_events()

        note.submit_for_review()

        assert note.status is ClinicalNoteStatus.IN_REVIEW
        events = note.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ClinicalNoteStatusChanged)
        assert events[0].status == "in_review"

    def test_submitting_an_already_in_review_note_is_idempotent(self) -> None:
        note = _make_note()
        note.submit_for_review()
        note.pull_events()
        note.submit_for_review()
        assert note.pull_events() == []

    def test_submit_for_review_while_signed_is_rejected(self) -> None:
        note = _make_note()
        note.sign(signed_at=datetime(2026, 1, 1, 10, 0), signed_by=uuid4())
        with pytest.raises(ClinicalNoteNotEditableError):
            note.submit_for_review()

    def test_submit_for_review_while_locked_is_rejected(self) -> None:
        note = _make_note()
        note.sign(signed_at=datetime(2026, 1, 1, 10, 0), signed_by=uuid4())
        note.lock(locked_at=datetime(2026, 1, 1, 11, 0))
        with pytest.raises(ClinicalNoteNotEditableError):
            note.submit_for_review()


class TestSign:
    def test_sign_from_draft_sets_status_and_signature_and_records_event(self) -> None:
        note = _make_note()
        note.pull_events()
        signed_at = datetime(2026, 1, 1, 10, 0)
        signed_by = uuid4()

        note.sign(signed_at=signed_at, signed_by=signed_by)

        assert note.status is ClinicalNoteStatus.SIGNED
        assert note.signature == Signature(signed_at=signed_at, signed_by=signed_by)
        events = note.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ClinicalNoteStatusChanged)
        assert events[0].status == "signed"

    def test_sign_from_in_review_is_accepted(self) -> None:
        note = _make_note()
        note.submit_for_review()

        note.sign(signed_at=datetime(2026, 1, 1, 10, 0), signed_by=uuid4())

        assert note.status is ClinicalNoteStatus.SIGNED

    def test_signing_an_already_signed_note_is_rejected(self) -> None:
        note = _make_note()
        note.sign(signed_at=datetime(2026, 1, 1, 10, 0), signed_by=uuid4())
        with pytest.raises(ClinicalNoteNotEditableError):
            note.sign(signed_at=datetime(2026, 1, 1, 11, 0), signed_by=uuid4())

    def test_signing_a_locked_note_is_rejected(self) -> None:
        note = _make_note()
        note.sign(signed_at=datetime(2026, 1, 1, 10, 0), signed_by=uuid4())
        note.lock(locked_at=datetime(2026, 1, 1, 11, 0))
        with pytest.raises(ClinicalNoteNotEditableError):
            note.sign(signed_at=datetime(2026, 1, 1, 12, 0), signed_by=uuid4())


class TestLock:
    def test_lock_sets_status_and_locked_at_and_records_event(self) -> None:
        note = _make_note()
        note.sign(signed_at=datetime(2026, 1, 1, 10, 0), signed_by=uuid4())
        note.pull_events()
        locked_at = datetime(2026, 1, 1, 11, 0)

        note.lock(locked_at=locked_at)

        assert note.status is ClinicalNoteStatus.LOCKED
        assert note.locked_at == locked_at
        events = note.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ClinicalNoteStatusChanged)
        assert events[0].status == "locked"

    def test_lock_from_draft_is_rejected(self) -> None:
        note = _make_note()
        with pytest.raises(LockRequiresSignedNoteError):
            note.lock(locked_at=datetime(2026, 1, 1, 11, 0))

    def test_lock_from_in_review_is_rejected(self) -> None:
        note = _make_note()
        note.submit_for_review()
        with pytest.raises(LockRequiresSignedNoteError):
            note.lock(locked_at=datetime(2026, 1, 1, 11, 0))

    def test_locking_an_already_locked_note_is_rejected(self) -> None:
        note = _make_note()
        note.sign(signed_at=datetime(2026, 1, 1, 10, 0), signed_by=uuid4())
        note.lock(locked_at=datetime(2026, 1, 1, 11, 0))
        with pytest.raises(LockRequiresSignedNoteError):
            note.lock(locked_at=datetime(2026, 1, 1, 12, 0))


class TestSignatureConsistency:
    @pytest.mark.parametrize("status", [ClinicalNoteStatus.SIGNED, ClinicalNoteStatus.LOCKED])
    def test_signed_or_locked_without_signature_is_rejected(
        self, status: ClinicalNoteStatus
    ) -> None:
        with pytest.raises(SignatureRequiredError):
            _make_raw_note(
                status=status,
                signature=None,
                locked_at=(
                    datetime(2026, 1, 1, 11, 0) if status is ClinicalNoteStatus.LOCKED else None
                ),
            )

    @pytest.mark.parametrize("status", [ClinicalNoteStatus.DRAFT, ClinicalNoteStatus.IN_REVIEW])
    def test_draft_or_in_review_with_signature_is_rejected(
        self, status: ClinicalNoteStatus
    ) -> None:
        with pytest.raises(SignatureNotAllowedError):
            signature = Signature(signed_at=datetime(2026, 1, 1, 10, 0), signed_by=uuid4())
            _make_raw_note(status=status, signature=signature)


class TestLockedAtConsistency:
    def test_locked_without_locked_at_is_rejected(self) -> None:
        with pytest.raises(LockedAtRequiredError):
            _make_raw_note(
                status=ClinicalNoteStatus.LOCKED,
                signature=Signature(signed_at=datetime(2026, 1, 1, 10, 0), signed_by=uuid4()),
                locked_at=None,
            )

    @pytest.mark.parametrize(
        "status",
        [ClinicalNoteStatus.DRAFT, ClinicalNoteStatus.IN_REVIEW, ClinicalNoteStatus.SIGNED],
    )
    def test_non_locked_with_locked_at_is_rejected(self, status: ClinicalNoteStatus) -> None:
        signature = (
            Signature(signed_at=datetime(2026, 1, 1, 10, 0), signed_by=uuid4())
            if status is ClinicalNoteStatus.SIGNED
            else None
        )
        with pytest.raises(LockedAtNotAllowedError):
            _make_raw_note(
                status=status, signature=signature, locked_at=datetime(2026, 1, 1, 11, 0)
            )
