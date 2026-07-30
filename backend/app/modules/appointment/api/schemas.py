"""Pydantic v2 request/response schemas for the Appointment module.

Not yet wired to any route — `api/router.py` registers no endpoints in
this phase (this task explicitly excludes API endpoints). Schemas never
expose a domain entity directly, and never accept server-controlled
fields (`id`, `organization_id`, `status`, `checked_in_at`,
`completed_at`, `cancelled_at`, ...) from the client — see
`docs/backend-architecture/07_security_layer.md §7` (mass-assignment
prevention). `organization_id` in particular is never client-settable at
all: it is always derived from the linked `Patient` — see
`domain/entities.py`.
"""

from datetime import date, time
from uuid import UUID

from pydantic import Field

from app.modules.appointment.domain.enums import AppointmentStatus, AppointmentType
from app.schemas.base import ORJSONModel


class AppointmentResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    patient_id: UUID
    doctor_id: UUID
    appointment_number: str
    appointment_date: date
    start_time: time
    end_time: time
    appointment_type: AppointmentType
    status: AppointmentStatus
    reason_for_visit: str | None = None
    notes: str | None = None
    booked_by_user_id: UUID | None = None
    visit_id: UUID | None = None


class CreateAppointmentRequest(ORJSONModel):
    patient_id: UUID
    doctor_id: UUID
    appointment_number: str = Field(max_length=64)
    appointment_date: date
    start_time: time
    end_time: time
    appointment_type: AppointmentType
    reason_for_visit: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)
    booked_by_user_id: UUID | None = None


class UpdateAppointmentRequest(ORJSONModel):
    appointment_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    appointment_type: AppointmentType | None = None
    reason_for_visit: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)


class CompleteAppointmentRequest(ORJSONModel):
    visit_id: UUID | None = None
