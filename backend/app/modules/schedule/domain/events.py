"""Domain events published by Schedule/Availability module aggregates.

Recorded on an aggregate via `record_event()` and only actually published
(to the `EventBus`) after the transaction that raised them commits
successfully — see `app.shared.application.unit_of_work.UnitOfWork` and
`docs/backend-architecture/10_module_communication.md`.
"""

from dataclasses import dataclass
from uuid import UUID

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class DoctorScheduleCreated(DomainEvent):
    schedule_id: UUID
    organization_id: UUID
    doctor_id: UUID


@dataclass(frozen=True, kw_only=True)
class DoctorScheduleUpdated(DomainEvent):
    schedule_id: UUID


@dataclass(frozen=True, kw_only=True)
class DoctorScheduleActiveChanged(DomainEvent):
    schedule_id: UUID
    is_active: bool


@dataclass(frozen=True, kw_only=True)
class DoctorTimeOffCreated(DomainEvent):
    time_off_id: UUID
    organization_id: UUID
    doctor_id: UUID


@dataclass(frozen=True, kw_only=True)
class DoctorTimeOffUpdated(DomainEvent):
    time_off_id: UUID
