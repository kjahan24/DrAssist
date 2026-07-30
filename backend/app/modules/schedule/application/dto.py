"""Data Transfer Objects for the Schedule/Availability module's
application layer.

Distinct from both domain entities (never leave the module) and API
schemas (this task builds no HTTP endpoint — see `api/router.py`).
Use-case input/output DTOs are plain, immutable dataclasses;
`DoctorScheduleSummaryDTO`/`DoctorTimeOffSummaryDTO` are also re-exported
from `public/dto.py` for other modules to depend on.

Neither `CreateDoctorScheduleInput` nor `CreateDoctorTimeOffInput` has an
`organization_id` field — see `domain/entities.py` for why it is always
derived from the linked `Doctor`.
"""

from dataclasses import dataclass
from datetime import datetime, time
from uuid import UUID

from app.modules.schedule.domain.enums import Weekday

# --- CreateDoctorSchedule ---------------------------------------------------


@dataclass(frozen=True, slots=True)
class CreateDoctorScheduleInput:
    doctor_id: UUID
    weekday: Weekday
    start_time: time
    end_time: time
    slot_duration_minutes: int
    is_active: bool = True
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class CreateDoctorScheduleOutput:
    schedule_id: UUID
    organization_id: UUID
    doctor_id: UUID
    weekday: Weekday


# --- UpdateDoctorSchedule ----------------------------------------------------


@dataclass(frozen=True, slots=True)
class UpdateDoctorScheduleInput:
    schedule_id: UUID
    start_time: time | None = None
    end_time: time | None = None
    slot_duration_minutes: int | None = None


@dataclass(frozen=True, slots=True)
class UpdateDoctorScheduleOutput:
    schedule_id: UUID


# --- Activate/DeactivateDoctorSchedule ---------------------------------------


@dataclass(frozen=True, slots=True)
class ActivateDoctorScheduleInput:
    schedule_id: UUID


@dataclass(frozen=True, slots=True)
class DeactivateDoctorScheduleInput:
    schedule_id: UUID


@dataclass(frozen=True, slots=True)
class DoctorScheduleActiveOutput:
    schedule_id: UUID
    is_active: bool


# --- CreateDoctorTimeOff ------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CreateDoctorTimeOffInput:
    doctor_id: UUID
    start_datetime: datetime
    end_datetime: datetime
    reason: str | None = None
    created_by: UUID | None = None


@dataclass(frozen=True, slots=True)
class CreateDoctorTimeOffOutput:
    time_off_id: UUID
    organization_id: UUID
    doctor_id: UUID


# --- UpdateDoctorTimeOff --------------------------------------------------------


@dataclass(frozen=True, slots=True)
class UpdateDoctorTimeOffInput:
    time_off_id: UUID
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateDoctorTimeOffOutput:
    time_off_id: UUID


# --- Cross-cutting read models (also re-exported via public/dto.py) --------


@dataclass(frozen=True, slots=True)
class DoctorScheduleSummaryDTO:
    schedule_id: UUID
    organization_id: UUID
    doctor_id: UUID
    weekday: Weekday
    start_time: time
    end_time: time
    slot_duration_minutes: int
    is_active: bool


@dataclass(frozen=True, slots=True)
class DoctorTimeOffSummaryDTO:
    time_off_id: UUID
    organization_id: UUID
    doctor_id: UUID
    start_datetime: datetime
    end_datetime: datetime
    reason: str | None
