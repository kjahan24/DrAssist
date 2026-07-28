"""Domain events published by Patient module aggregates.

Recorded on an aggregate via `record_event()` and only actually published
(to the `EventBus`) after the transaction that raised them commits
successfully — see `app.shared.application.unit_of_work.UnitOfWork` and
`docs/backend-architecture/10_module_communication.md`.
"""

from dataclasses import dataclass
from uuid import UUID

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class PatientRegistered(DomainEvent):
    patient_id: UUID
    organization_id: UUID
    patient_number: str


@dataclass(frozen=True, kw_only=True)
class PatientDetailsUpdated(DomainEvent):
    patient_id: UUID
    organization_id: UUID


@dataclass(frozen=True, kw_only=True)
class PatientStatusChanged(DomainEvent):
    patient_id: UUID
    organization_id: UUID
    status: str


@dataclass(frozen=True, kw_only=True)
class PatientContactAdded(DomainEvent):
    contact_id: UUID
    patient_id: UUID
    contact_type: str
    is_primary: bool


@dataclass(frozen=True, kw_only=True)
class PatientContactUpdated(DomainEvent):
    contact_id: UUID
    patient_id: UUID


@dataclass(frozen=True, kw_only=True)
class EmergencyContactAdded(DomainEvent):
    contact_id: UUID
    patient_id: UUID
    is_primary: bool


@dataclass(frozen=True, kw_only=True)
class EmergencyContactUpdated(DomainEvent):
    contact_id: UUID
    patient_id: UUID


@dataclass(frozen=True, kw_only=True)
class InsuranceAdded(DomainEvent):
    insurance_id: UUID
    patient_id: UUID
    policy_number: str


@dataclass(frozen=True, kw_only=True)
class InsuranceUpdated(DomainEvent):
    insurance_id: UUID
    patient_id: UUID


@dataclass(frozen=True, kw_only=True)
class InsuranceStatusChanged(DomainEvent):
    insurance_id: UUID
    patient_id: UUID
    status: str
