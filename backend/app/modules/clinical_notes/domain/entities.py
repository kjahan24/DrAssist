"""Clinical Notes module aggregate root: `ClinicalNote`.

This is the **master record for every future clinical document** — SOAP
Note, Prescription, Lab Order, Lab Result, Imaging Report, Clinical
Reasoning, Differential Diagnosis, ICD-10/CPT Coding, AI Copilot, Doctor
Review, and Clinical Timeline are all expected to reference
`clinical_note_id` from their own tables (see
`app.modules.clinical_notes.container`'s scope note) — nothing here
needs to change for that: a stable UUID primary key and the public
`ClinicalNoteQueryPort` are the entire contract those future modules
need, per this task's own "Future Compatibility" requirement.

Unlike the five prior Visit sub-modules, `ClinicalNote` references
`Visit` (`visit_id`), `Patient` (`patient_id`), *and* `Doctor`
(`doctor_id`, the authoring/responsible doctor — not necessarily the
visit's own attending doctor; a covering physician or specialist may
document a note on someone else's visit) — the same three-reference
shape `PatientVisit` itself uses for `Patient`/`Doctor`, not the
"derive everything from one visit" shape `VisitVitalSigns` etc. use. The
application layer resolves `patient_id` via `Visit`'s own summary rather
than a separate `PatientQueryPort` call: since `PatientVisit.patient_id`
is already a validated reference, checking `visit_summary.patient_id ==
patient_id` both confirms the patient exists *and* that this visit
actually belongs to them — see
`application/use_cases/create_clinical_note.py`.

`Signature` (`value_objects.py`) is the one value object this module
needs — see that module's own docstring. No value object wraps
`note_number`: no format is specified, the same reasoning
`app.modules.diagnosis.domain.entities` documents for `icd10_code`.

Status is a small, strict workflow: `Draft` -> `In Review` -> `Signed`
-> `Locked`, matching this task's own explicit rules almost verbatim:
- "Draft notes can be edited" / "Signed notes become read-only" /
  "Locked notes cannot be modified" -> `update_details()` (and
  `submit_for_review()`) only succeed while `status is DRAFT`; only
  `Draft` is ever named as editable, so every other status is treated as
  not editable by default, the conservative reading for clinical
  documentation state.
- "Locked notes must already be Signed" -> `lock()` requires
  `status is SIGNED` *before* transitioning, not merely that a signature
  exists — a note cannot skip straight from Draft/In Review to Locked.
- "signed_at exists only when status = Signed or Locked" / "signed_by
  exists only when..." -> collapsed into one bidirectional check on
  `signature` (see `_validate_signature_consistency`), since the two
  fields are one `Signature` now.
- `locked_at` gets the identical bidirectional treatment
  (`_validate_locked_at_consistency`) even though this task's Business
  Rules section only states it for `signed_at`/`signed_by` — a
  `locked_at` that could exist independently of `status = Locked` (or be
  absent *at* Locked) has no plausible meaning for a field whose entire
  purpose is "when this note was locked", so leaving it unvalidated
  would be an inconsistency in the same aggregate, not a genuinely
  unconstrained field like `ai_model`.

All mutation goes through named methods that enforce the aggregate's
invariants and record domain events; nothing here performs I/O.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

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
from app.shared.domain.entity import AggregateRoot

_SIGNATURE_STATUSES = frozenset({ClinicalNoteStatus.SIGNED, ClinicalNoteStatus.LOCKED})
_NOT_EDITABLE_STATUSES = frozenset({ClinicalNoteStatus.SIGNED, ClinicalNoteStatus.LOCKED})


@dataclass(kw_only=True, eq=False)
class ClinicalNote(AggregateRoot):
    organization_id: UUID
    patient_id: UUID
    visit_id: UUID
    doctor_id: UUID
    note_number: str
    note_type: ClinicalNoteType
    encounter_datetime: datetime
    status: ClinicalNoteStatus = ClinicalNoteStatus.DRAFT
    chief_complaint_summary: str | None = None
    history_summary: str | None = None
    examination_summary: str | None = None
    assessment_summary: str | None = None
    plan_summary: str | None = None
    ai_generated: bool = False
    ai_model: str | None = None
    ai_version: str | None = None
    signature: Signature | None = None
    locked_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.note_number or not self.note_number.strip():
            raise NoteNumberRequiredError()
        self.note_number = self.note_number.strip()
        _validate_signature_consistency(self.status, self.signature)
        _validate_locked_at_consistency(self.status, self.locked_at)

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        patient_id: UUID,
        visit_id: UUID,
        doctor_id: UUID,
        note_number: str,
        note_type: ClinicalNoteType,
        encounter_datetime: datetime,
        chief_complaint_summary: str | None = None,
        history_summary: str | None = None,
        examination_summary: str | None = None,
        assessment_summary: str | None = None,
        plan_summary: str | None = None,
        ai_generated: bool = False,
        ai_model: str | None = None,
        ai_version: str | None = None,
    ) -> "ClinicalNote":
        """A note always starts `Draft`, unsigned, and unlocked —
        `status`, `signature`, and `locked_at` are therefore not
        constructor parameters; they're only ever set later via
        `submit_for_review()`, `sign()`, and `lock()`."""
        note = cls(
            organization_id=organization_id,
            patient_id=patient_id,
            visit_id=visit_id,
            doctor_id=doctor_id,
            note_number=note_number,
            note_type=note_type,
            encounter_datetime=encounter_datetime,
            chief_complaint_summary=chief_complaint_summary,
            history_summary=history_summary,
            examination_summary=examination_summary,
            assessment_summary=assessment_summary,
            plan_summary=plan_summary,
            ai_generated=ai_generated,
            ai_model=ai_model,
            ai_version=ai_version,
        )
        note.record_event(
            ClinicalNoteCreated(
                clinical_note_id=note.id,
                organization_id=organization_id,
                patient_id=patient_id,
                visit_id=visit_id,
                note_number=note.note_number,
            )
        )
        return note

    def update_details(
        self,
        *,
        note_type: ClinicalNoteType | None = None,
        encounter_datetime: datetime | None = None,
        chief_complaint_summary: str | None = None,
        history_summary: str | None = None,
        examination_summary: str | None = None,
        assessment_summary: str | None = None,
        plan_summary: str | None = None,
        ai_generated: bool | None = None,
        ai_model: str | None = None,
        ai_version: str | None = None,
    ) -> None:
        """`note_number`, `status`, `signature`, and `locked_at` are
        deliberately not parameters here — `note_number` is a permanent
        identifier, and the workflow fields change only through
        `submit_for_review()`/`sign()`/`lock()`, the same distinction
        `app.modules.diagnosis.domain.entities.VisitDiagnosis
        .update_details` draws by excluding its own status."""
        self._ensure_editable()
        if note_type is not None:
            self.note_type = note_type
        if encounter_datetime is not None:
            self.encounter_datetime = encounter_datetime
        if chief_complaint_summary is not None:
            self.chief_complaint_summary = chief_complaint_summary
        if history_summary is not None:
            self.history_summary = history_summary
        if examination_summary is not None:
            self.examination_summary = examination_summary
        if assessment_summary is not None:
            self.assessment_summary = assessment_summary
        if plan_summary is not None:
            self.plan_summary = plan_summary
        if ai_generated is not None:
            self.ai_generated = ai_generated
        if ai_model is not None:
            self.ai_model = ai_model
        if ai_version is not None:
            self.ai_version = ai_version

        self.touch()
        self.record_event(ClinicalNoteUpdated(clinical_note_id=self.id, visit_id=self.visit_id))

    def submit_for_review(self) -> None:
        if self.status in _NOT_EDITABLE_STATUSES:
            raise ClinicalNoteNotEditableError()
        self._set_status(ClinicalNoteStatus.IN_REVIEW)

    def sign(self, *, signed_at: datetime, signed_by: UUID) -> None:
        if self.status in _NOT_EDITABLE_STATUSES:
            raise ClinicalNoteNotEditableError()
        self.status = ClinicalNoteStatus.SIGNED
        self.signature = Signature(signed_at=signed_at, signed_by=signed_by)
        self.touch()
        self.record_event(
            ClinicalNoteStatusChanged(
                clinical_note_id=self.id, visit_id=self.visit_id, status=self.status.value
            )
        )

    def lock(self, *, locked_at: datetime) -> None:
        if self.status is not ClinicalNoteStatus.SIGNED:
            raise LockRequiresSignedNoteError()
        self.status = ClinicalNoteStatus.LOCKED
        self.locked_at = locked_at
        self.touch()
        self.record_event(
            ClinicalNoteStatusChanged(
                clinical_note_id=self.id, visit_id=self.visit_id, status=self.status.value
            )
        )

    def _ensure_editable(self) -> None:
        if self.status is not ClinicalNoteStatus.DRAFT:
            raise ClinicalNoteNotEditableError()

    def _set_status(self, status: ClinicalNoteStatus) -> None:
        if self.status is status:
            return
        self.status = status
        self.touch()
        self.record_event(
            ClinicalNoteStatusChanged(
                clinical_note_id=self.id, visit_id=self.visit_id, status=status.value
            )
        )


def _validate_signature_consistency(
    status: ClinicalNoteStatus, signature: Signature | None
) -> None:
    requires_signature = status in _SIGNATURE_STATUSES
    if requires_signature and signature is None:
        raise SignatureRequiredError()
    if not requires_signature and signature is not None:
        raise SignatureNotAllowedError()


def _validate_locked_at_consistency(status: ClinicalNoteStatus, locked_at: datetime | None) -> None:
    if status is ClinicalNoteStatus.LOCKED and locked_at is None:
        raise LockedAtRequiredError()
    if status is not ClinicalNoteStatus.LOCKED and locked_at is not None:
        raise LockedAtNotAllowedError()
