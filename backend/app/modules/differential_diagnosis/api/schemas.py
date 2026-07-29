"""Pydantic v2 request/response schemas for the Differential Diagnosis
module.

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

from app.modules.differential_diagnosis.domain.enums import DiagnosisSource, ReviewStatus
from app.schemas.base import ORJSONModel


class DifferentialDiagnosisResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    clinical_note_id: UUID
    clinical_reasoning_id: UUID | None = None
    patient_id: UUID
    visit_id: UUID
    doctor_id: UUID
    diagnosis_name: str
    diagnosis_source: DiagnosisSource
    ranking: int
    likelihood_score: float | None = None
    supporting_evidence: str | None = None
    excluded: bool
    review_status: ReviewStatus


class CreateDifferentialDiagnosisRequest(ORJSONModel):
    clinical_note_id: UUID
    clinical_reasoning_id: UUID | None = None
    diagnosis_name: str = Field(max_length=500)
    diagnosis_source: DiagnosisSource
    ranking: int = Field(ge=1)
    likelihood_score: float | None = None
    supporting_evidence: str | None = Field(default=None, max_length=4000)
    excluded: bool = False


class UpdateDifferentialDiagnosisRequest(ORJSONModel):
    diagnosis_name: str | None = Field(default=None, max_length=500)
    likelihood_score: float | None = None
    supporting_evidence: str | None = Field(default=None, max_length=4000)
    excluded: bool | None = None
