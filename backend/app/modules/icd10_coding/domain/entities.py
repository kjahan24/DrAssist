"""ICD-10 Coding module aggregate root: `ICD10Coding`.

`ICD10Coding` extends `ClinicalNote` — it does not replace it, and it is
**one-to-many**: "One Clinical Note may contain multiple ICD-10 codes" —
the same shape `app.modules.differential_diagnosis.domain.entities
.DifferentialDiagnosis`/`app.modules.clinical_reasoning.domain.entities
.ClinicalReasoning` already establish for their own place under
`ClinicalNote`. `organization_id`, `patient_id`, `visit_id`, and
`doctor_id` are still not independently caller-supplied: the application
layer derives every one of them from the referenced `ClinicalNote`'s own
summary (see `application/use_cases/create_icd10_coding.py`), the
identical "true by construction" technique every prior child-document
module uses.

**This module never checks the parent's editability.** Neither
`ClinicalNoteQueryPort.is_editable` nor `DifferentialDiagnosisQueryPort
.is_editable` is ever called — this task's Business Rules state
immutability only for this aggregate's *own* `review_status` ("Approved
and Rejected codes become read-only"), the same "only encode business
rules explicitly stated for the module being built" reasoning
`app.modules.differential_diagnosis.domain.entities.DifferentialDiagnosis`
already establishes.

**Starting `review_status` is derived from `coding_source`** — "AI-
generated codes start as Pending" / "Physician-generated codes start as
Reviewed" are both unconditional starting-state rules; `create()`
computes `review_status` from `coding_source`: `Physician` starts
`Reviewed`; `AI` and `Hybrid` both start `Pending`, the identical
conservative reading `DifferentialDiagnosis.create()` already applies to
its own `diagnosis_source`.

**"Only one ICD-10 code can be marked as Primary" is the same shape**
`app.modules.diagnosis.domain.entities.VisitDiagnosis` already
establishes for "Only one Primary diagnosis is allowed per Visit" —
enforced as *rejection* (`DuplicatePrimaryCodeError`, raised by the
application layer after querying siblings — see
`application/use_cases/create_icd10_coding.py`/
`mark_icd10_coding_as_primary.py`), not silent auto-unset: which code is
principal/primary carries real billing and compliance weight, so
demoting a sibling code without anyone asking to change it would corrupt
clinical/billing data, the identical reasoning `VisitDiagnosis` documents
for its own `diagnosis_type`. Unlike `VisitDiagnosis.diagnosis_type`
(fixed at creation, no update path), `primary_code` here is a plain
boolean with two dedicated transition methods, `mark_as_primary()`/
`unmark_as_primary()` — promoting/demoting a code after the fact is a
realistic coding workflow this task's own boolean field (rather than a
fixed enum choice) implies is expected to change.

**"Duplicate ICD-10 prevention within a Clinical Note" is enforced with
normalized-case matching** — unlike
`DifferentialDiagnosis.diagnosis_name` (free text, compared case-
insensitively only at the application layer, since no database
functional index was requested), `icd10_code` is a standardized code
system where case carries no meaning under WHO/CMS ICD-10-CM convention,
so `__post_init__` normalizes it to uppercase (the same lightweight,
non-arbitrary normalization `note_number`/`diagnosis_name` already apply
via `.strip()`). This is what lets the *database* enforce true uniqueness
too — see `infrastructure/models.py` for the partial unique index this
normalization makes possible.

No value object wraps `icd10_code`: this task's own Business Rules state
no format (only *duplication* rules), the identical reasoning
`app.modules.diagnosis.domain.entities` documents for its own,
identically-named `icd10_code` field — "inventing an unrequested format
constraint here would be scope creep." `diagnosis_title`/`coding_notes`
have no stated format either, the same reasoning applied throughout this
codebase for free-text fields.

All mutation goes through named methods that enforce the aggregate's
invariants and record domain events; nothing here performs I/O.
"""

from dataclasses import dataclass
from uuid import UUID

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
from app.shared.domain.entity import AggregateRoot

_EDITABLE_STATUSES = frozenset({ReviewStatus.PENDING, ReviewStatus.REVIEWED})
_STARTS_REVIEWED_SOURCES = frozenset({CodingSource.PHYSICIAN})


@dataclass(kw_only=True, eq=False)
class ICD10Coding(AggregateRoot):
    organization_id: UUID
    clinical_note_id: UUID
    patient_id: UUID
    visit_id: UUID
    doctor_id: UUID
    icd10_code: str
    diagnosis_title: str
    coding_source: CodingSource
    review_status: ReviewStatus
    differential_diagnosis_id: UUID | None = None
    primary_code: bool = False
    coding_notes: str | None = None

    def __post_init__(self) -> None:
        if not self.icd10_code or not self.icd10_code.strip():
            raise ICD10CodeRequiredError()
        self.icd10_code = self.icd10_code.strip().upper()
        if not self.diagnosis_title or not self.diagnosis_title.strip():
            raise DiagnosisTitleRequiredError()
        self.diagnosis_title = self.diagnosis_title.strip()

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        clinical_note_id: UUID,
        patient_id: UUID,
        visit_id: UUID,
        doctor_id: UUID,
        icd10_code: str,
        diagnosis_title: str,
        coding_source: CodingSource,
        differential_diagnosis_id: UUID | None = None,
        primary_code: bool = False,
        coding_notes: str | None = None,
    ) -> "ICD10Coding":
        coding = cls(
            organization_id=organization_id,
            clinical_note_id=clinical_note_id,
            patient_id=patient_id,
            visit_id=visit_id,
            doctor_id=doctor_id,
            icd10_code=icd10_code,
            diagnosis_title=diagnosis_title,
            coding_source=coding_source,
            review_status=(
                ReviewStatus.REVIEWED
                if coding_source in _STARTS_REVIEWED_SOURCES
                else ReviewStatus.PENDING
            ),
            differential_diagnosis_id=differential_diagnosis_id,
            primary_code=primary_code,
            coding_notes=coding_notes,
        )
        coding.record_event(
            ICD10CodingCreated(
                icd10_coding_id=coding.id,
                organization_id=organization_id,
                clinical_note_id=clinical_note_id,
            )
        )
        return coding

    def ensure_editable(self) -> None:
        """Shared by `update_details()`, `mark_as_primary()`,
        `unmark_as_primary()`, `approve()`, and `reject()`: `review_status`
        must not already be `Approved`/`Rejected`."""
        if self.review_status not in _EDITABLE_STATUSES:
            raise ICD10CodingNotEditableError()

    def update_details(
        self, *, diagnosis_title: str | None = None, coding_notes: str | None = None
    ) -> None:
        """`icd10_code`, `coding_source`, `differential_diagnosis_id`, and
        every identity field are deliberately not parameters here — they
        are immutable once set, the same treatment
        `app.modules.clinical_notes.domain.entities.ClinicalNote` gives
        its own `note_number`."""
        self.ensure_editable()
        if diagnosis_title is not None:
            if not diagnosis_title.strip():
                raise DiagnosisTitleRequiredError()
            self.diagnosis_title = diagnosis_title.strip()
        if coding_notes is not None:
            self.coding_notes = coding_notes

        self.touch()
        self.record_event(
            ICD10CodingUpdated(icd10_coding_id=self.id, clinical_note_id=self.clinical_note_id)
        )

    def mark_as_primary(self) -> None:
        """Whether a sibling code is already Primary for this Clinical
        Note is *not* checked here — that invariant spans multiple rows
        and belongs to the application layer; see the module docstring."""
        self.ensure_editable()
        self._set_primary(True)

    def unmark_as_primary(self) -> None:
        self.ensure_editable()
        self._set_primary(False)

    def _set_primary(self, primary_code: bool) -> None:
        if self.primary_code is primary_code:
            return
        self.primary_code = primary_code
        self.touch()
        self.record_event(
            ICD10CodingPrimaryChanged(
                icd10_coding_id=self.id,
                clinical_note_id=self.clinical_note_id,
                primary_code=primary_code,
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
            ICD10CodingReviewStatusChanged(
                icd10_coding_id=self.id,
                clinical_note_id=self.clinical_note_id,
                review_status=review_status.value,
            )
        )
