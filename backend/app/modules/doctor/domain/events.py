"""Domain events published by Doctor module aggregates.

Recorded on an aggregate via `record_event()` and only actually published
(to the `EventBus`) after the transaction that raised them commits
successfully — see `app.shared.application.unit_of_work.UnitOfWork` and
`docs/backend-architecture/10_module_communication.md`.
"""

from dataclasses import dataclass
from uuid import UUID

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class DoctorOnboarded(DomainEvent):
    doctor_id: UUID
    organization_id: UUID
    user_id: UUID
    employee_id: str


@dataclass(frozen=True, kw_only=True)
class DoctorActivated(DomainEvent):
    doctor_id: UUID


@dataclass(frozen=True, kw_only=True)
class DoctorDeactivated(DomainEvent):
    doctor_id: UUID


@dataclass(frozen=True, kw_only=True)
class DoctorSuspended(DomainEvent):
    doctor_id: UUID


@dataclass(frozen=True, kw_only=True)
class DoctorProfileCreated(DomainEvent):
    doctor_id: UUID
    profile_id: UUID


@dataclass(frozen=True, kw_only=True)
class DoctorProfileUpdated(DomainEvent):
    doctor_id: UUID
    profile_id: UUID


@dataclass(frozen=True, kw_only=True)
class DoctorLicenseAdded(DomainEvent):
    license_id: UUID
    doctor_id: UUID
    license_number: str


@dataclass(frozen=True, kw_only=True)
class DoctorLicenseVerified(DomainEvent):
    license_id: UUID
    doctor_id: UUID


@dataclass(frozen=True, kw_only=True)
class DoctorLicenseRejected(DomainEvent):
    license_id: UUID
    doctor_id: UUID


@dataclass(frozen=True, kw_only=True)
class DoctorSpecializationAdded(DomainEvent):
    specialization_id: UUID
    doctor_id: UUID
    specialization_name: str
    is_primary: bool


@dataclass(frozen=True, kw_only=True)
class DoctorScheduleAdded(DomainEvent):
    schedule_id: UUID
    doctor_id: UUID
    day_of_week: str
