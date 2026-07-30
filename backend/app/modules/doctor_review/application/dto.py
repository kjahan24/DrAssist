"""Data Transfer Objects for the Doctor Review module's application
layer.

Distinct from both domain entities (never leave the module) and API
schemas (this task builds no HTTP endpoint — see `api/router.py`).
Use-case input/output DTOs are plain, immutable dataclasses;
`DoctorReviewSummaryDTO` is also re-exported from `public/dto.py` for
other modules to depend on.

`CreateDoctorReviewInput` deliberately has no `organization_id`/
`patient_id`/`visit_id`/`doctor_id` fields — see `domain/entities.py`
for why those are always derived from the linked `ClinicalNote`. It also
has no `review_status` field — a new review always starts `Pending`.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.doctor_review.domain.enums import ReviewStatus

# --- CreateDoctorReview -------------------------------------------------


@dataclass(frozen=True, slots=True)
class CreateDoctorReviewInput:
    clinical_note_id: UUID
    review_comment: str | None = None
    approved_clinical_note: bool = False
    approved_soap_note: bool = False
    approved_prescription: bool = False
    approved_lab_orders: bool = False
    approved_lab_results: bool = False
    approved_reasoning: bool = False
    approved_differential_diagnosis: bool = False
    approved_icd10: bool = False
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class CreateDoctorReviewOutput:
    doctor_review_id: UUID
    organization_id: UUID
    clinical_note_id: UUID
    review_status: ReviewStatus


# --- UpdateDoctorReview --------------------------------------------------


@dataclass(frozen=True, slots=True)
class UpdateDoctorReviewInput:
    doctor_review_id: UUID
    review_comment: str | None = None
    approved_clinical_note: bool | None = None
    approved_soap_note: bool | None = None
    approved_prescription: bool | None = None
    approved_lab_orders: bool | None = None
    approved_lab_results: bool | None = None
    approved_reasoning: bool | None = None
    approved_differential_diagnosis: bool | None = None
    approved_icd10: bool | None = None


@dataclass(frozen=True, slots=True)
class UpdateDoctorReviewOutput:
    doctor_review_id: UUID
    clinical_note_id: UUID


# --- Review workflow transitions -----------------------------------------


@dataclass(frozen=True, slots=True)
class ApproveDoctorReviewInput:
    doctor_review_id: UUID


@dataclass(frozen=True, slots=True)
class RejectDoctorReviewInput:
    doctor_review_id: UUID


@dataclass(frozen=True, slots=True)
class ReturnDoctorReviewForRevisionInput:
    doctor_review_id: UUID


@dataclass(frozen=True, slots=True)
class DoctorReviewStatusOutput:
    doctor_review_id: UUID
    clinical_note_id: UUID
    review_status: ReviewStatus
    reviewed_at: datetime | None


# --- Cross-cutting read model (also re-exported via public/dto.py) --------


@dataclass(frozen=True, slots=True)
class DoctorReviewSummaryDTO:
    doctor_review_id: UUID
    organization_id: UUID
    patient_id: UUID
    visit_id: UUID
    doctor_id: UUID
    clinical_note_id: UUID
    review_status: ReviewStatus
    review_comment: str | None
    reviewed_at: datetime | None
    approved_clinical_note: bool
    approved_soap_note: bool
    approved_prescription: bool
    approved_lab_orders: bool
    approved_lab_results: bool
    approved_reasoning: bool
    approved_differential_diagnosis: bool
    approved_icd10: bool
