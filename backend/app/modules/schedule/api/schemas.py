"""Pydantic v2 request/response schemas for the Schedule/Availability
module.

Wired to `api/router.py`'s live endpoints (added by a later REST APIs
task; this module's own founding task explicitly excluded HTTP endpoints
— see `container.py`'s scope note). Schemas never expose a domain entity
directly, and never accept server-controlled fields (`id`,
`organization_id`, `is_active`, ...) from the client — see
`docs/backend-architecture/07_security_layer.md §7` (mass-assignment
prevention). `organization_id` in particular is never client-settable at
all: it is always derived from the linked `Doctor` — see
`domain/entities.py`.
"""

from datetime import datetime, time
from uuid import UUID

from pydantic import Field

from app.modules.schedule.domain.enums import Weekday
from app.schemas.base import ORJSONModel


class DoctorScheduleResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    doctor_id: UUID
    weekday: Weekday
    start_time: time
    end_time: time
    slot_duration_minutes: int
    is_active: bool


class CreateDoctorScheduleRequest(ORJSONModel):
    doctor_id: UUID
    weekday: Weekday
    start_time: time
    end_time: time
    slot_duration_minutes: int = Field(gt=0)
    is_active: bool = True


class UpdateDoctorScheduleRequest(ORJSONModel):
    start_time: time | None = None
    end_time: time | None = None
    slot_duration_minutes: int | None = Field(default=None, gt=0)


class DoctorTimeOffResponse(ORJSONModel):
    id: UUID
    organization_id: UUID
    doctor_id: UUID
    start_datetime: datetime
    end_datetime: datetime
    reason: str | None = None


class CreateDoctorTimeOffRequest(ORJSONModel):
    doctor_id: UUID
    start_datetime: datetime
    end_datetime: datetime
    reason: str | None = Field(default=None, max_length=2000)


class UpdateDoctorTimeOffRequest(ORJSONModel):
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    reason: str | None = Field(default=None, max_length=2000)
