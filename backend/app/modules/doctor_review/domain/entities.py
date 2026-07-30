"""Doctor Review module aggregate root: `DoctorReview`.

`DoctorReview` extends `ClinicalNote` — it does not replace it. It is a
**one-to-zero-or-one** child of a specific `ClinicalNote`
(`clinical_note_id`, unique), the same one-to-one shape
`app.modules.soap_notes.domain.entities.SOAPNote` uses, but — unlike
`SOAPNote`/`Prescription` — this aggregate *does* own its own status
lifecycle (`ReviewStatus`), the same self-governing shape
`app.modules.icd10_coding.domain.entities.ICD10Coding` establishes for
its own place under `ClinicalNote`. `organization_id`, `patient_id`,
`visit_id`, and `doctor_id` are not independently caller-supplied here at
all — the application layer derives every one of them from the
referenced `ClinicalNote`'s own summary (see
`application/use_cases/create_doctor_review.py`), which is what makes
"Patient, Visit, Organization, and Doctor must match the linked Clinical
Note" true by construction rather than something to validate after the
fact — the identical technique every prior child-document module in this
codebase uses.

**Represents the physician's final review before a clinical record
becomes part of the patient's permanent medical record** — a single
decision (`ReviewStatus`) plus an explicit checklist of which
documentation categories (SOAP Note, Prescription, Lab Orders, Lab
Results, Clinical Reasoning, Differential Diagnosis, ICD-10 Coding, and
the Clinical Note itself) the physician confirms as reviewed. This
module deliberately does **not** mutate those other modules' own
records — it only *reads* their existence through their public ports
(see `application/services/doctor_review_consistency_service.py`) and
records the physician's attestation as booleans on its own row. Cascading
an approval into flipping every other module's own `review_status`/
`approve()` was considered and rejected: no business rule stated here
asks for it, doing so would require this module to hold write access to
eight other aggregates' invariants (a significant, unrequested expansion
of blast radius), and the stated Future Compatibility items (Electronic
Signature, Multi-stage Approval, Quality Assurance Review, Hospital
Review Committee) are exactly the natural home for that richer
orchestration later — see `container.py`'s scope note.

**Status lifecycle** — `ReviewStatus.PENDING` is the only starting state
(there is no `coding_source`/`diagnosis_source`-style alternate starting
state here, since nothing about the review's origin varies the way an
AI- vs. physician-authored record's starting status did in
`ICD10Coding`/`DifferentialDiagnosis`). `PENDING` and
`RETURNED_FOR_REVISION` are editable ("ReturnedForRevision keeps the
record editable"); `APPROVED` and `REJECTED` are terminal ("Approved
makes the entire clinical encounter read-only" / "Rejected also becomes
immutable") — enforced by `ensure_editable()`, shared by
`update_details()` and every transition method. "Review status
transitions must be validated" is enforced by an explicit
`_ALLOWED_TRANSITIONS` map rather than a bare `ensure_editable()` check.
The map deliberately excludes `RETURNED_FOR_REVISION -> RETURNED_FOR_REVISION`
and any transition back to `PENDING`: this task's Business Rules never
describe a resubmission cycle, so nothing beyond
`{PENDING, RETURNED_FOR_REVISION} -> {APPROVED, REJECTED}` plus
`PENDING -> RETURNED_FOR_REVISION` is implemented — adding an unrequested
resubmit-to-Pending transition would be scope creep this module does not
need, and the transition map can grow to support one later without a
schema change.

**"Approved makes the entire clinical encounter read-only"** is read
literally as scoped to *this aggregate's own* editability, the same
"only encode business rules explicitly stated for the module being
built" principle `app.modules.icd10_coding.domain.entities.ICD10Coding`
and `app.modules.differential_diagnosis.domain.entities
.DifferentialDiagnosis` already establish: this module does not reach
into `ClinicalNote`/`SOAPNote`/etc. to lock them, since none of those
modules were asked to consume a new "is the encounter reviewed" signal in
this task, and rule 1 ("never modify previous modules unless absolutely
necessary") governs. Exposing that signal for other modules to *later*
consume is exactly what `public/interfaces.DoctorReviewQueryPort
.is_editable` is for.

**"reviewed_at is automatically populated once review leaves Pending"**
is read literally: `reviewed_at` is set exactly once, the first time
`review_status` changes away from `PENDING`, and is never overwritten by
a later transition (`_transition_to()` only sets it `if self.reviewed_at
is None`).

No value object wraps any field here: the five identity/reference FKs
have no invariant intrinsic to themselves (the same reasoning
`app.modules.soap_notes.domain.entities.SOAPNote` documents for its own
identical shape), `review_comment` is a plain nullable free-text field
with no stated format, and the eight `approved_*` fields are plain
booleans with a cross-*module* existence invariant enforced by
`application/services/doctor_review_consistency_service.py` (I/O,
therefore not something `__post_init__` can check).

All mutation goes through named methods that enforce the aggregate's
invariants and record domain events; nothing here performs I/O.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

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
from app.shared.domain.entity import AggregateRoot

_EDITABLE_STATUSES = frozenset({ReviewStatus.PENDING, ReviewStatus.RETURNED_FOR_REVISION})

_ALLOWED_TRANSITIONS: dict[ReviewStatus, frozenset[ReviewStatus]] = {
    ReviewStatus.PENDING: frozenset(
        {ReviewStatus.APPROVED, ReviewStatus.REJECTED, ReviewStatus.RETURNED_FOR_REVISION}
    ),
    ReviewStatus.RETURNED_FOR_REVISION: frozenset({ReviewStatus.APPROVED, ReviewStatus.REJECTED}),
    ReviewStatus.APPROVED: frozenset(),
    ReviewStatus.REJECTED: frozenset(),
}


@dataclass(kw_only=True, eq=False)
class DoctorReview(AggregateRoot):
    organization_id: UUID
    patient_id: UUID
    visit_id: UUID
    doctor_id: UUID
    clinical_note_id: UUID
    review_status: ReviewStatus
    review_comment: str | None = None
    reviewed_at: datetime | None = None
    approved_clinical_note: bool = False
    approved_soap_note: bool = False
    approved_prescription: bool = False
    approved_lab_orders: bool = False
    approved_lab_results: bool = False
    approved_reasoning: bool = False
    approved_differential_diagnosis: bool = False
    approved_icd10: bool = False

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        patient_id: UUID,
        visit_id: UUID,
        doctor_id: UUID,
        clinical_note_id: UUID,
        review_comment: str | None = None,
        approved_clinical_note: bool = False,
        approved_soap_note: bool = False,
        approved_prescription: bool = False,
        approved_lab_orders: bool = False,
        approved_lab_results: bool = False,
        approved_reasoning: bool = False,
        approved_differential_diagnosis: bool = False,
        approved_icd10: bool = False,
    ) -> "DoctorReview":
        review = cls(
            organization_id=organization_id,
            patient_id=patient_id,
            visit_id=visit_id,
            doctor_id=doctor_id,
            clinical_note_id=clinical_note_id,
            review_status=ReviewStatus.PENDING,
            review_comment=review_comment,
            approved_clinical_note=approved_clinical_note,
            approved_soap_note=approved_soap_note,
            approved_prescription=approved_prescription,
            approved_lab_orders=approved_lab_orders,
            approved_lab_results=approved_lab_results,
            approved_reasoning=approved_reasoning,
            approved_differential_diagnosis=approved_differential_diagnosis,
            approved_icd10=approved_icd10,
        )
        review.record_event(
            DoctorReviewCreated(
                doctor_review_id=review.id,
                organization_id=organization_id,
                clinical_note_id=clinical_note_id,
            )
        )
        return review

    def ensure_editable(self) -> None:
        """Shared by `update_details()` and every transition method:
        `review_status` must not already be `Approved`/`Rejected`."""
        if self.review_status not in _EDITABLE_STATUSES:
            raise DoctorReviewNotEditableError()

    def update_details(
        self,
        *,
        review_comment: str | None = None,
        approved_clinical_note: bool | None = None,
        approved_soap_note: bool | None = None,
        approved_prescription: bool | None = None,
        approved_lab_orders: bool | None = None,
        approved_lab_results: bool | None = None,
        approved_reasoning: bool | None = None,
        approved_differential_diagnosis: bool | None = None,
        approved_icd10: bool | None = None,
    ) -> None:
        """`None` means "leave unchanged" for every parameter — the same
        partial-update convention
        `app.modules.icd10_coding.domain.entities.ICD10Coding
        .update_details()` uses. `organization_id`/`patient_id`/
        `visit_id`/`doctor_id`/`clinical_note_id`/`review_status` are
        deliberately not parameters here: they are immutable once set."""
        self.ensure_editable()
        if review_comment is not None:
            self.review_comment = review_comment
        if approved_clinical_note is not None:
            self.approved_clinical_note = approved_clinical_note
        if approved_soap_note is not None:
            self.approved_soap_note = approved_soap_note
        if approved_prescription is not None:
            self.approved_prescription = approved_prescription
        if approved_lab_orders is not None:
            self.approved_lab_orders = approved_lab_orders
        if approved_lab_results is not None:
            self.approved_lab_results = approved_lab_results
        if approved_reasoning is not None:
            self.approved_reasoning = approved_reasoning
        if approved_differential_diagnosis is not None:
            self.approved_differential_diagnosis = approved_differential_diagnosis
        if approved_icd10 is not None:
            self.approved_icd10 = approved_icd10

        self.touch()
        self.record_event(
            DoctorReviewUpdated(doctor_review_id=self.id, clinical_note_id=self.clinical_note_id)
        )

    def approve(self) -> None:
        self._transition_to(ReviewStatus.APPROVED)

    def reject(self) -> None:
        self._transition_to(ReviewStatus.REJECTED)

    def return_for_revision(self) -> None:
        self._transition_to(ReviewStatus.RETURNED_FOR_REVISION)

    def _transition_to(self, target_status: ReviewStatus) -> None:
        allowed = _ALLOWED_TRANSITIONS.get(self.review_status, frozenset())
        if target_status not in allowed:
            raise InvalidReviewStatusTransitionError(self.review_status.value, target_status.value)
        self.review_status = target_status
        if self.reviewed_at is None:
            self.reviewed_at = datetime.now(UTC)
        self.touch()
        self.record_event(
            DoctorReviewStatusChanged(
                doctor_review_id=self.id,
                clinical_note_id=self.clinical_note_id,
                review_status=target_status.value,
            )
        )
