"""Pydantic v2 request/response schemas for the ICD-10 Coding module.

Not yet wired to any route — `api/router.py` registers no endpoints in
this phase. Schemas never expose a domain entity directly, and never
accept server-controlled fields (`id`, `organization_id`, `patient_id`,
`visit_id`, `doctor_id`, `review_status`, ...) from the client — see
`docs/backend-architecture/07_security_layer.md §7` (mass-assignment
prevention). `patient_id`/`visit_id`/`doctor_id`/`organization_id` in
particular are never client-settable at all: they are always derived
from the linked `ClinicalNote` — see `domain/entities.py`.
"""

from uuid import UUID

from pydantic import Field

from app.modules.icd10_coding.domain.enums import CodingSource, ReviewStatus
from app.schemas.base import ORJSONModel


class ICD10CodingResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    clinical_note_id: UUID
    differential_diagnosis_id: UUID | None = None
    patient_id: UUID
    visit_id: UUID
    doctor_id: UUID
    icd10_code: str
    diagnosis_title: str
    coding_source: CodingSource
    primary_code: bool
    review_status: ReviewStatus
    coding_notes: str | None = None


class CreateICD10CodingRequest(ORJSONModel):
    clinical_note_id: UUID
    differential_diagnosis_id: UUID | None = None
    icd10_code: str = Field(max_length=10)
    diagnosis_title: str = Field(max_length=500)
    coding_source: CodingSource
    primary_code: bool = False
    coding_notes: str | None = Field(default=None, max_length=2000)


class UpdateICD10CodingRequest(ORJSONModel):
    diagnosis_title: str | None = Field(default=None, max_length=500)
    coding_notes: str | None = Field(default=None, max_length=2000)
