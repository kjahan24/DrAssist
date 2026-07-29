"""Pydantic v2 request/response schemas for the Diagnosis module.

Not yet wired to any route — `api/router.py` registers no endpoints in
this phase. Schemas never expose a domain entity directly, and never
accept server-controlled fields (`id`, `organization_id`, ...) from the
client — see `docs/backend-architecture/07_security_layer.md §7`
(mass-assignment prevention).
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.modules.diagnosis.domain.enums import DiagnosisStatus, DiagnosisType
from app.schemas.base import ORJSONModel


class VisitDiagnosisResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    visit_id: UUID
    sequence_number: int
    diagnosis_name: str
    icd10_code: str | None = None
    diagnosis_type: DiagnosisType
    diagnosis_status: DiagnosisStatus
    clinical_notes: str | None = None
    diagnosed_by: UUID | None = None
    diagnosed_at: datetime


class RecordVisitDiagnosisRequest(ORJSONModel):
    visit_id: UUID
    sequence_number: int = Field(ge=1)
    diagnosis_name: str = Field(min_length=1, max_length=500)
    diagnosis_type: DiagnosisType
    diagnosed_at: datetime
    icd10_code: str | None = Field(default=None, max_length=20)
    diagnosis_status: DiagnosisStatus = DiagnosisStatus.PROVISIONAL
    clinical_notes: str | None = Field(default=None, max_length=1000)
    diagnosed_by: UUID | None = None
