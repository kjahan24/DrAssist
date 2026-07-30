"""Pydantic v2 request/response schemas for the Doctor Review module.

Not yet wired to any route — `api/router.py` registers no endpoints in
this phase (this task explicitly excludes API endpoints). Schemas never
expose a domain entity directly, and never accept server-controlled
fields (`id`, `organization_id`, `patient_id`, `visit_id`, `doctor_id`,
`review_status`, `reviewed_at`, ...) from the client — see
`docs/backend-architecture/07_security_layer.md §7` (mass-assignment
prevention). `patient_id`/`visit_id`/`doctor_id`/`organization_id` in
particular are never client-settable at all: they are always derived
from the linked `ClinicalNote` — see `domain/entities.py`.
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.modules.doctor_review.domain.enums import ReviewStatus
from app.schemas.base import ORJSONModel


class DoctorReviewResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    patient_id: UUID
    visit_id: UUID
    doctor_id: UUID
    clinical_note_id: UUID
    review_status: ReviewStatus
    review_comment: str | None = None
    reviewed_at: datetime | None = None
    approved_clinical_note: bool
    approved_soap_note: bool
    approved_prescription: bool
    approved_lab_orders: bool
    approved_lab_results: bool
    approved_reasoning: bool
    approved_differential_diagnosis: bool
    approved_icd10: bool


class CreateDoctorReviewRequest(ORJSONModel):
    clinical_note_id: UUID
    review_comment: str | None = Field(default=None, max_length=2000)
    approved_clinical_note: bool = False
    approved_soap_note: bool = False
    approved_prescription: bool = False
    approved_lab_orders: bool = False
    approved_lab_results: bool = False
    approved_reasoning: bool = False
    approved_differential_diagnosis: bool = False
    approved_icd10: bool = False


class UpdateDoctorReviewRequest(ORJSONModel):
    review_comment: str | None = Field(default=None, max_length=2000)
    approved_clinical_note: bool | None = None
    approved_soap_note: bool | None = None
    approved_prescription: bool | None = None
    approved_lab_orders: bool | None = None
    approved_lab_results: bool | None = None
    approved_reasoning: bool | None = None
    approved_differential_diagnosis: bool | None = None
    approved_icd10: bool | None = None
