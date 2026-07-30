"""Pydantic v2 request/response schemas for the Patient History module.

Not yet wired to any route — `api/router.py` registers no endpoints in
this phase (this task explicitly excludes API endpoints). Schemas never
expose a domain entity directly, and never accept server-controlled
fields (`id`, `organization_id`, `patient_id`, `visit_id`, ...) from the
client — see `docs/backend-architecture/07_security_layer.md §7`
(mass-assignment prevention). `organization_id`/`patient_id`/`visit_id`
in particular are never client-settable at all: they are always derived
from the linked, approved `DoctorReview` — see `domain/entities.py`.

There is no `Update...Request` schema: "History records are immutable."
"""

from datetime import date
from uuid import UUID

from pydantic import Field

from app.modules.patient_history.domain.enums import HistoryType, ReferenceType
from app.schemas.base import ORJSONModel


class PatientHistoryResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    patient_id: UUID
    visit_id: UUID
    doctor_review_id: UUID
    history_type: HistoryType
    reference_type: ReferenceType
    reference_id: UUID
    encounter_date: date
    summary: str
    created_from_review: bool


class CreatePatientHistoryRequest(ORJSONModel):
    doctor_review_id: UUID
    history_type: HistoryType
    reference_type: ReferenceType
    reference_id: UUID
    encounter_date: date
    summary: str = Field(max_length=4000)
