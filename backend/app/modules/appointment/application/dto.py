"""Data Transfer Objects for the Appointment module's application layer.

Distinct from both domain entities (never leave the module) and API
schemas (this task builds no HTTP endpoint — see `api/router.py`).
Use-case input/output DTOs are plain, immutable dataclasses;
`AppointmentSummaryDTO` is also re-exported from `public/dto.py` for
other modules to depend on.

`CreateAppointmentInput` deliberately has no `organization_id` field —
see `domain/entities.py` for why it is always derived from the linked
`Patient` (and validated against the linked `Doctor`'s own organization).
It also has no `status` field — a new appointment always starts
`Scheduled`.
"""

from dataclasses import dataclass
from datetime import date, datetime, time
from uuid import UUID

from app.modules.appointment.domain.enums import AppointmentStatus, AppointmentType

# --- CreateAppointment ----------------------------------------------------


@dataclass(frozen=True, slots=True)
class CreateAppointmentInput:
    patient_id: UUID
    doctor_id: UUID
    appointment_number: str
    appointment_date: date
    start_time: time
    end_time: time
    appointment_type: AppointmentType
    reason_for_visit: str | None = None
    notes: str | None = None
    booked_by_user_id: UUID | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class CreateAppointmentOutput:
    appointment_id: UUID
    organization_id: UUID
    appointment_number: str
    status: AppointmentStatus


# --- UpdateAppointment ------------------------------------------------------


@dataclass(frozen=True, slots=True)
class UpdateAppointmentInput:
    appointment_id: UUID
    appointment_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    appointment_type: AppointmentType | None = None
    reason_for_visit: str | None = None
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateAppointmentOutput:
    appointment_id: UUID


# --- Status workflow transitions -------------------------------------------


@dataclass(frozen=True, slots=True)
class ConfirmAppointmentInput:
    appointment_id: UUID


@dataclass(frozen=True, slots=True)
class CheckInAppointmentInput:
    appointment_id: UUID


@dataclass(frozen=True, slots=True)
class StartAppointmentInput:
    appointment_id: UUID


@dataclass(frozen=True, slots=True)
class CompleteAppointmentInput:
    appointment_id: UUID
    visit_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class CancelAppointmentInput:
    appointment_id: UUID


@dataclass(frozen=True, slots=True)
class MarkAppointmentNoShowInput:
    appointment_id: UUID


@dataclass(frozen=True, slots=True)
class AppointmentStatusOutput:
    appointment_id: UUID
    status: AppointmentStatus


# --- Cross-cutting read model (also re-exported via public/dto.py) --------


@dataclass(frozen=True, slots=True)
class AppointmentSummaryDTO:
    appointment_id: UUID
    organization_id: UUID
    patient_id: UUID
    doctor_id: UUID
    appointment_number: str
    appointment_date: date
    start_time: time
    end_time: time
    appointment_type: AppointmentType
    status: AppointmentStatus
    reason_for_visit: str | None
    notes: str | None
    booked_by_user_id: UUID | None
    visit_id: UUID | None
    checked_in_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None

    @property
    def id(self) -> UUID:
        """Alias for `appointment_id`, added by the REST APIs task.

        `api/schemas.py`'s `AppointmentResponse.id` (and every other
        module's `<X>Response.id`) uses the uniform field name `id`, while
        this DTO — like every other module's Summary DTO — keeps its own
        domain-meaningful primary-key name (`appointment_id`) for its
        existing non-API callers. `ORJSONModel.model_validate(summary)`
        (`from_attributes=True`) reads `id` via plain attribute access, so
        a read-only property bridges the two without renaming the
        canonical field or touching any existing caller. The same
        property is added to every other module's Summary DTO for the
        same reason — see this docstring as the shared rationale."""
        return self.appointment_id
