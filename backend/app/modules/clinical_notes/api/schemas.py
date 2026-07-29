"""Pydantic v2 request/response schemas for the Clinical Notes module.

Not yet wired to any route — `api/router.py` registers no endpoints in
this phase. Schemas never expose a domain entity directly, and never
accept server-controlled fields (`id`, `organization_id`, `status`,
`signed_at`, `signed_by`, `locked_at`, ...) from the client — see
`docs/backend-architecture/07_security_layer.md §7` (mass-assignment
prevention).
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.modules.clinical_notes.domain.enums import ClinicalNoteStatus, ClinicalNoteType
from app.schemas.base import ORJSONModel


class ClinicalNoteResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    patient_id: UUID
    visit_id: UUID
    doctor_id: UUID
    note_number: str
    note_type: ClinicalNoteType
    status: ClinicalNoteStatus
    encounter_datetime: datetime
    chief_complaint_summary: str | None = None
    history_summary: str | None = None
    examination_summary: str | None = None
    assessment_summary: str | None = None
    plan_summary: str | None = None
    ai_generated: bool
    ai_model: str | None = None
    ai_version: str | None = None
    signed_at: datetime | None = None
    signed_by: UUID | None = None
    locked_at: datetime | None = None


class CreateClinicalNoteRequest(ORJSONModel):
    patient_id: UUID
    visit_id: UUID
    doctor_id: UUID
    note_number: str = Field(min_length=1, max_length=64)
    note_type: ClinicalNoteType
    encounter_datetime: datetime
    chief_complaint_summary: str | None = Field(default=None, max_length=2000)
    history_summary: str | None = Field(default=None, max_length=4000)
    examination_summary: str | None = Field(default=None, max_length=4000)
    assessment_summary: str | None = Field(default=None, max_length=4000)
    plan_summary: str | None = Field(default=None, max_length=4000)
    ai_generated: bool = False
    ai_model: str | None = Field(default=None, max_length=100)
    ai_version: str | None = Field(default=None, max_length=50)
