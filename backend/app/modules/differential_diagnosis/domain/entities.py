"""Differential Diagnosis module aggregate root: `DifferentialDiagnosis`.

`DifferentialDiagnosis` extends `ClinicalNote` — it does not replace it,
and it is **one-to-many**: "One Clinical Note may have multiple
Differential Diagnoses" — the same shape
`app.modules.clinical_reasoning.domain.entities.ClinicalReasoning`/
`app.modules.lab_orders.domain.entities.LabOrder` already establish for
their own place under `ClinicalNote`. `organization_id`, `patient_id`,
`visit_id`, and `doctor_id` are still not independently caller-supplied:
the application layer derives every one of them from the referenced
`ClinicalNote`'s own summary (see
`application/use_cases/create_differential_diagnosis.py`), the identical
"true by construction" technique every prior child-document module uses.

**This module never checks the parent's editability.** Neither
`ClinicalNoteQueryPort.is_editable` nor `ClinicalReasoningQueryPort
.is_editable` is ever called — this task's Business Rules state
immutability only for this aggregate's *own* `review_status` ("Approved
and Rejected diagnoses become read-only"), the same "only encode business
rules explicitly stated for the module being built" reasoning
`app.modules.clinical_reasoning.domain.entities.ClinicalReasoning` already
establishes. `ensure_editable()` therefore checks only this aggregate's
own `review_status`.

**Starting `review_status` is derived from `diagnosis_source`, not
independently supplied** — "AI-generated diagnoses always start as
Pending" / "Physician-authored diagnoses start as Reviewed" are both
unconditional starting-state rules. Unlike `ClinicalReasoning` (which has
a separate `ai_generated` boolean alongside `reasoning_source`), this
task's own field list gives `DifferentialDiagnosis` no such boolean — only
`diagnosis_source` — so `create()` derives `review_status` from
`diagnosis_source` directly: `Physician` starts `Reviewed`; `AI` and
`Hybrid` both start `Pending`, since a `Hybrid` diagnosis still has AI
involvement a physician has not yet reviewed, and only a purely
physician-authored diagnosis has an authoring act that itself constitutes
review — the conservative reading, matching this codebase's established
"only explicitly named states are treated as already-satisfying a rule"
convention.

`ranking` must be unique *within a Clinical Note* — enforced two ways,
the same defense-in-depth split `app.modules.diagnosis.domain.entities
.VisitDiagnosis` already establishes for its own `sequence_number`:
`__post_init__` rejects `ranking < 1` (a single-row check, so it belongs
here), while cross-row uniqueness against sibling diagnoses requires a
repository query and therefore belongs to the application layer (see
`application/use_cases/create_differential_diagnosis.py`) and a partial
unique DB index (see `infrastructure/models.py`). `ranking` has no
update path — like `order_number`/`prescription_number`, it is treated as
immutable once set, since no business rule describes reordering.

"Duplicate diagnosis prevention" (this task's own Validation section) is
a *second*, independent check from ranking uniqueness: no two
(non-deleted) `DifferentialDiagnosis` rows for the same `ClinicalNote` may
share a `diagnosis_name` (case-insensitively) — also a cross-row check,
so it too lives in the application layer, not here.

"If linked to Clinical Reasoning, both records must belong to the same
Clinical Note" is a cross-*module* consistency check (requires
`ClinicalReasoningQueryPort`), so it is enforced entirely at the
application layer — see `application/use_cases
/create_differential_diagnosis.py`.

No value object wraps any field: `diagnosis_name`/`supporting_evidence`
have no stated format (the same reasoning
`app.modules.diagnosis.domain.entities` documents for `icd10_code`), and
`likelihood_score` has no stated range or precision, the same reasoning
`app.modules.clinical_reasoning.domain.entities.ClinicalReasoning`
documents for `confidence_score`. None of this aggregate's fields have a
genuine *intrinsic*, self-contained multi-field invariant (the bar this
codebase's existing value objects — `BloodPressure`, `Signature` — both
meet), so none is introduced here either.

All mutation goes through named methods that enforce the aggregate's
invariants and record domain events; nothing here performs I/O.
"""

from dataclasses import dataclass
from uuid import UUID

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
from app.shared.domain.entity import AggregateRoot

_MIN_RANKING = 1
_EDITABLE_STATUSES = frozenset({ReviewStatus.PENDING, ReviewStatus.REVIEWED})
_STARTS_REVIEWED_SOURCES = frozenset({DiagnosisSource.PHYSICIAN})


@dataclass(kw_only=True, eq=False)
class DifferentialDiagnosis(AggregateRoot):
    organization_id: UUID
    clinical_note_id: UUID
    patient_id: UUID
    visit_id: UUID
    doctor_id: UUID
    diagnosis_name: str
    diagnosis_source: DiagnosisSource
    ranking: int
    review_status: ReviewStatus
    clinical_reasoning_id: UUID | None = None
    likelihood_score: float | None = None
    supporting_evidence: str | None = None
    excluded: bool = False

    def __post_init__(self) -> None:
        if not self.diagnosis_name or not self.diagnosis_name.strip():
            raise DiagnosisNameRequiredError()
        self.diagnosis_name = self.diagnosis_name.strip()
        if self.ranking < _MIN_RANKING:
            raise InvalidRankingError(self.ranking)

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        clinical_note_id: UUID,
        patient_id: UUID,
        visit_id: UUID,
        doctor_id: UUID,
        diagnosis_name: str,
        diagnosis_source: DiagnosisSource,
        ranking: int,
        clinical_reasoning_id: UUID | None = None,
        likelihood_score: float | None = None,
        supporting_evidence: str | None = None,
        excluded: bool = False,
    ) -> "DifferentialDiagnosis":
        diagnosis = cls(
            organization_id=organization_id,
            clinical_note_id=clinical_note_id,
            patient_id=patient_id,
            visit_id=visit_id,
            doctor_id=doctor_id,
            diagnosis_name=diagnosis_name,
            diagnosis_source=diagnosis_source,
            ranking=ranking,
            review_status=(
                ReviewStatus.REVIEWED
                if diagnosis_source in _STARTS_REVIEWED_SOURCES
                else ReviewStatus.PENDING
            ),
            clinical_reasoning_id=clinical_reasoning_id,
            likelihood_score=likelihood_score,
            supporting_evidence=supporting_evidence,
            excluded=excluded,
        )
        diagnosis.record_event(
            DifferentialDiagnosisCreated(
                differential_diagnosis_id=diagnosis.id,
                organization_id=organization_id,
                clinical_note_id=clinical_note_id,
            )
        )
        return diagnosis

    def ensure_editable(self) -> None:
        """Shared by `update_details()`, `approve()`, and `reject()`:
        `review_status` must not already be `Approved`/`Rejected`."""
        if self.review_status not in _EDITABLE_STATUSES:
            raise DifferentialDiagnosisNotEditableError()

    def update_details(
        self,
        *,
        diagnosis_name: str | None = None,
        likelihood_score: float | None = None,
        supporting_evidence: str | None = None,
        excluded: bool | None = None,
    ) -> None:
        """`ranking`, `diagnosis_source`, `clinical_reasoning_id`, and
        every identity field are deliberately not parameters here — they
        are immutable once set, the same treatment
        `app.modules.clinical_notes.domain.entities.ClinicalNote` gives
        its own `note_number`."""
        self.ensure_editable()
        if diagnosis_name is not None:
            if not diagnosis_name.strip():
                raise DiagnosisNameRequiredError()
            self.diagnosis_name = diagnosis_name.strip()
        if likelihood_score is not None:
            self.likelihood_score = likelihood_score
        if supporting_evidence is not None:
            self.supporting_evidence = supporting_evidence
        if excluded is not None:
            self.excluded = excluded

        self.touch()
        self.record_event(
            DifferentialDiagnosisUpdated(
                differential_diagnosis_id=self.id, clinical_note_id=self.clinical_note_id
            )
        )

    def mark_reviewed(self) -> None:
        if self.review_status is not ReviewStatus.PENDING:
            raise ReviewRequiresPendingStatusError()
        self._set_review_status(ReviewStatus.REVIEWED)

    def approve(self) -> None:
        self.ensure_editable()
        self._set_review_status(ReviewStatus.APPROVED)

    def reject(self) -> None:
        self.ensure_editable()
        self._set_review_status(ReviewStatus.REJECTED)

    def _set_review_status(self, review_status: ReviewStatus) -> None:
        self.review_status = review_status
        self.touch()
        self.record_event(
            DifferentialDiagnosisReviewStatusChanged(
                differential_diagnosis_id=self.id,
                clinical_note_id=self.clinical_note_id,
                review_status=review_status.value,
            )
        )
