"""Domain events published by Visit module aggregates.

Recorded on an aggregate via `record_event()` and only actually published
(to the `EventBus`) after the transaction that raised them commits
successfully — see `app.shared.application.unit_of_work.UnitOfWork` and
`docs/backend-architecture/10_module_communication.md`.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class PatientVisitScheduled(DomainEvent):
    visit_id: UUID
    organization_id: UUID
    patient_id: UUID
    doctor_id: UUID
    visit_number: str


@dataclass(frozen=True, kw_only=True)
class PatientVisitUpdated(DomainEvent):
    visit_id: UUID
    patient_id: UUID


@dataclass(frozen=True, kw_only=True)
class PatientVisitCheckedIn(DomainEvent):
    visit_id: UUID
    patient_id: UUID
    check_in_time: datetime


@dataclass(frozen=True, kw_only=True)
class PatientVisitConsultationStarted(DomainEvent):
    visit_id: UUID
    patient_id: UUID
    consultation_start_time: datetime


@dataclass(frozen=True, kw_only=True)
class PatientVisitCompleted(DomainEvent):
    visit_id: UUID
    patient_id: UUID
    consultation_end_time: datetime


@dataclass(frozen=True, kw_only=True)
class PatientVisitCheckedOut(DomainEvent):
    visit_id: UUID
    patient_id: UUID
    check_out_time: datetime


@dataclass(frozen=True, kw_only=True)
class PatientVisitStatusChanged(DomainEvent):
    visit_id: UUID
    patient_id: UUID
    status: str
