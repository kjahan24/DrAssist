"""Pydantic v2 request/response schemas for the SOAP Notes module.

Not yet wired to any route — `api/router.py` registers no endpoints in
this phase. Schemas never expose a domain entity directly, and never
accept server-controlled fields (`id`, `organization_id`, `patient_id`,
`visit_id`, `doctor_id`, ...) from the client — see
`docs/backend-architecture/07_security_layer.md §7` (mass-assignment
prevention). `patient_id`/`visit_id`/`doctor_id`/`organization_id` in
particular are never client-settable at all: they are always derived
from the linked `ClinicalNote` — see `domain/entities.py`.
"""

from uuid import UUID

from pydantic import Field

from app.schemas.base import ORJSONModel


class SOAPNoteResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    clinical_note_id: UUID
    patient_id: UUID
    visit_id: UUID
    doctor_id: UUID
    chief_complaint: str | None = None
    history_of_present_illness: str | None = None
    review_of_systems: str | None = None
    physical_examination: str | None = None
    vital_sign_summary: str | None = None
    assessment: str | None = None
    plan: str | None = None


class CreateSOAPNoteRequest(ORJSONModel):
    clinical_note_id: UUID
    chief_complaint: str | None = Field(default=None, max_length=2000)
    history_of_present_illness: str | None = Field(default=None, max_length=4000)
    review_of_systems: str | None = Field(default=None, max_length=4000)
    physical_examination: str | None = Field(default=None, max_length=4000)
    vital_sign_summary: str | None = Field(default=None, max_length=2000)
    assessment: str | None = Field(default=None, max_length=4000)
    plan: str | None = Field(default=None, max_length=4000)


class UpdateSOAPNoteRequest(ORJSONModel):
    chief_complaint: str | None = Field(default=None, max_length=2000)
    history_of_present_illness: str | None = Field(default=None, max_length=4000)
    review_of_systems: str | None = Field(default=None, max_length=4000)
    physical_examination: str | None = Field(default=None, max_length=4000)
    vital_sign_summary: str | None = Field(default=None, max_length=2000)
    assessment: str | None = Field(default=None, max_length=4000)
    plan: str | None = Field(default=None, max_length=4000)
