"""Clinical Reasoning module aggregate root: `ClinicalReasoning`.

`ClinicalReasoning` extends `ClinicalNote` — it does not replace it, and
it is **one-to-many**: "One Clinical Note may contain multiple Clinical
Reasoning records" — the same shape
`app.modules.lab_orders.domain.entities.LabOrder` already establishes for
its own place under `ClinicalNote` (not the strict one-to-one shape
`SOAPNote`/`Prescription` use). `organization_id`, `patient_id`,
`visit_id`, and `doctor_id` are still not independently caller-supplied:
the application layer derives every one of them from the referenced
`ClinicalNote`'s own summary (see
`application/use_cases/create_clinical_reasoning.py`), the identical
"true by construction" technique every prior child-document module uses.

**This module never checks the parent's editability.** `SOAPNote`,
`Prescription`, and `LabOrder` each also check
`ClinicalNoteQueryPort.is_editable` before allowing a write, because
their own task's business rules explicitly said so ("If the linked
Clinical Note is Signed or Locked, ... becomes read-only"). This task's
Business Rules say nothing of the kind — the only immutability rule
stated is entirely about this aggregate's *own* `review_status`
("Approved/Rejected reasoning becomes immutable"). Inventing a
cross-module check this task never asked for would be scope creep, the
same "only encode business rules explicitly stated for the module being
built" reasoning `app.modules.lab_results.domain.entities.LabResult`
already establishes for its own narrower read-only rule. `ensure_editable()`
therefore checks only this aggregate's own `review_status`, with no
cross-module port call anywhere in this module's use cases.

**Starting `review_status` is derived from `ai_generated`, not
independently supplied** — "AI-generated reasoning always starts as
Pending" / "Physician-authored reasoning starts as Reviewed" are both
unconditional *starting-state* rules, so `create()` computes
`review_status` from `ai_generated` rather than accepting it as a
parameter, the same "true by construction" technique used throughout this
module for the identity FKs. `reviewed_by_doctor` is derived alongside it
for the identical reason: a physician-authored record starting at
`Reviewed` has no plausible reviewer other than the authoring physician
themselves, so it starts `True` exactly when `ai_generated` is `False`
(and `False` when `ai_generated` is `True`, since nothing has reviewed an
AI-generated record yet). `reviewed_by_doctor` is otherwise only ever set
by `mark_reviewed()`/`approve()`/`reject()`, never a direct
`update_details()` parameter — the same "fields coupled to a status
transition change only through the named transition method" split
`app.modules.clinical_notes.domain.entities.ClinicalNote` draws for its
own `signed_at`.

`reasoning_source` (Physician/AI/Hybrid) and `ai_generated` (bool) are
deliberately independent fields — this task's own field list gives
`ClinicalReasoning` both, and no business rule ties `Hybrid` to a
specific value of `ai_generated`, so no cross-field consistency check is
invented between them (`ai_generated` alone is what the two starting-
state business rules are phrased in terms of).

No value object wraps any field: `reasoning_text` has no stated format
(the same reasoning `app.modules.diagnosis.domain.entities` documents for
`icd10_code`), and `confidence_score` has no stated range or precision —
this task's own Implement checklist, unlike every prior module's, does
not even list "Value Objects where appropriate", reinforcing that none is
expected here.

All mutation goes through named methods that enforce the aggregate's
invariants and record domain events; nothing here performs I/O.
"""

from dataclasses import dataclass
from uuid import UUID

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
from app.shared.domain.entity import AggregateRoot

_EDITABLE_STATUSES = frozenset({ReviewStatus.PENDING, ReviewStatus.REVIEWED})


@dataclass(kw_only=True, eq=False)
class ClinicalReasoning(AggregateRoot):
    organization_id: UUID
    clinical_note_id: UUID
    patient_id: UUID
    visit_id: UUID
    doctor_id: UUID
    reasoning_source: ReasoningSource
    reasoning_text: str
    ai_generated: bool
    review_status: ReviewStatus
    reviewed_by_doctor: bool
    confidence_score: float | None = None

    def __post_init__(self) -> None:
        if not self.reasoning_text or not self.reasoning_text.strip():
            raise ReasoningTextRequiredError()
        self.reasoning_text = self.reasoning_text.strip()

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        clinical_note_id: UUID,
        patient_id: UUID,
        visit_id: UUID,
        doctor_id: UUID,
        reasoning_source: ReasoningSource,
        reasoning_text: str,
        ai_generated: bool,
        confidence_score: float | None = None,
    ) -> "ClinicalReasoning":
        reasoning = cls(
            organization_id=organization_id,
            clinical_note_id=clinical_note_id,
            patient_id=patient_id,
            visit_id=visit_id,
            doctor_id=doctor_id,
            reasoning_source=reasoning_source,
            reasoning_text=reasoning_text,
            ai_generated=ai_generated,
            review_status=ReviewStatus.PENDING if ai_generated else ReviewStatus.REVIEWED,
            reviewed_by_doctor=not ai_generated,
            confidence_score=confidence_score,
        )
        reasoning.record_event(
            ClinicalReasoningCreated(
                clinical_reasoning_id=reasoning.id,
                organization_id=organization_id,
                clinical_note_id=clinical_note_id,
            )
        )
        return reasoning

    def ensure_editable(self) -> None:
        """Shared by `update_details()`, `approve()`, and `reject()`:
        `review_status` must not already be `Approved`/`Rejected`."""
        if self.review_status not in _EDITABLE_STATUSES:
            raise ClinicalReasoningNotEditableError()

    def update_details(
        self, *, reasoning_text: str | None = None, confidence_score: float | None = None
    ) -> None:
        """`reasoning_source`, `ai_generated`, and every identity field
        are deliberately not parameters here — they are immutable once
        set, the same treatment
        `app.modules.clinical_notes.domain.entities.ClinicalNote` gives
        its own `note_number`."""
        self.ensure_editable()
        if reasoning_text is not None:
            if not reasoning_text.strip():
                raise ReasoningTextRequiredError()
            self.reasoning_text = reasoning_text.strip()
        if confidence_score is not None:
            self.confidence_score = confidence_score

        self.touch()
        self.record_event(
            ClinicalReasoningUpdated(
                clinical_reasoning_id=self.id, clinical_note_id=self.clinical_note_id
            )
        )

    def mark_reviewed(self) -> None:
        if self.review_status is not ReviewStatus.PENDING:
            raise ReviewRequiresPendingStatusError()
        self.reviewed_by_doctor = True
        self._set_review_status(ReviewStatus.REVIEWED)

    def approve(self) -> None:
        self.ensure_editable()
        self.reviewed_by_doctor = True
        self._set_review_status(ReviewStatus.APPROVED)

    def reject(self) -> None:
        self.ensure_editable()
        self.reviewed_by_doctor = True
        self._set_review_status(ReviewStatus.REJECTED)

    def _set_review_status(self, review_status: ReviewStatus) -> None:
        self.review_status = review_status
        self.touch()
        self.record_event(
            ClinicalReasoningReviewStatusChanged(
                clinical_reasoning_id=self.id,
                clinical_note_id=self.clinical_note_id,
                review_status=review_status.value,
            )
        )
