"""Pydantic v2 request/response schemas for the Visit module.

Not yet wired to any route — `api/router.py` registers no endpoints in
this phase. Schemas never expose a domain entity directly, and never
accept server-controlled fields (`id`, `visit_status`, ...) from the
client — see `docs/backend-architecture/07_security_layer.md §7`
(mass-assignment prevention).
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import Field

from app.modules.visit.domain.enums import VisitPriority, VisitStatus, VisitType
from app.schemas.base import ORJSONModel


class PatientVisitResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    patient_id: UUID
    doctor_id: UUID
    visit_number: str
    appointment_id: UUID | None = None
    visit_type: VisitType
    visit_status: VisitStatus
    priority: VisitPriority
    visit_date: date
    check_in_time: datetime | None = None
    consultation_start_time: datetime | None = None
    consultation_end_time: datetime | None = None
    check_out_time: datetime | None = None
    chief_complaint_summary: str | None = None
    reason_for_visit: str | None = None
    room_number: str | None = None
    follow_up_required: bool
    follow_up_date: date | None = None
    notes: str | None = None


class ScheduleVisitRequest(ORJSONModel):
    patient_id: UUID
    doctor_id: UUID
    visit_number: str = Field(min_length=1, max_length=64)
    appointment_id: UUID | None = None
    visit_type: VisitType
    priority: VisitPriority = VisitPriority.NORMAL
    visit_date: date
    chief_complaint_summary: str | None = Field(default=None, max_length=500)
    reason_for_visit: str | None = Field(default=None, max_length=500)
    room_number: str | None = Field(default=None, max_length=50)
    follow_up_required: bool = False
    follow_up_date: date | None = None
    notes: str | None = Field(default=None, max_length=1000)
