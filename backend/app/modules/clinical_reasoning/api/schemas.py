"""Pydantic v2 request/response schemas for the Clinical Reasoning
module.

Not yet wired to any route — `api/router.py` registers no endpoints in
this phase. Schemas never expose a domain entity directly, and never
accept server-controlled fields (`id`, `organization_id`, `patient_id`,
`visit_id`, `doctor_id`, `review_status`, `reviewed_by_doctor`, ...) from
the client — see `docs/backend-architecture/07_security_layer.md §7`
(mass-assignment prevention). `patient_id`/`visit_id`/`doctor_id`/
`organization_id` in particular are never client-settable at all: they
are always derived from the linked `ClinicalNote` — see
`domain/entities.py`.
"""

from uuid import UUID

from pydantic import Field

from app.modules.clinical_reasoning.domain.enums import ReasoningSource, ReviewStatus
from app.schemas.base import ORJSONModel


class ClinicalReasoningResponse(ORJSONModel):
    id: UUID
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


class CreateClinicalReasoningRequest(ORJSONModel):
    clinical_note_id: UUID
    reasoning_source: ReasoningSource
    reasoning_text: str = Field(max_length=8000)
    ai_generated: bool
    confidence_score: float | None = None


class UpdateClinicalReasoningRequest(ORJSONModel):
    reasoning_text: str | None = Field(default=None, max_length=8000)
    confidence_score: float | None = None
