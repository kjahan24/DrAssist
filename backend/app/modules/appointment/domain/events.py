"""Domain events published by Appointment module aggregates.

Recorded on an aggregate via `record_event()` and only actually published
(to the `EventBus`) after the transaction that raised them commits
successfully — see `app.shared.application.unit_of_work.UnitOfWork` and
`docs/backend-architecture/10_module_communication.md`.

One generic `AppointmentStatusChanged` event backs every transition
(`confirm()`/`check_in()`/`start()`/`complete()`/`cancel()`/
`mark_no_show()`) rather than a distinct event per action — the same
minimal shape `app.modules.doctor_review.domain.events
.DoctorReviewStatusChanged` already establishes for its own multi-action
transition set.
"""

from dataclasses import dataclass
from uuid import UUID

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class AppointmentCreated(DomainEvent):
    appointment_id: UUID
    organization_id: UUID
    patient_id: UUID
    doctor_id: UUID


@dataclass(frozen=True, kw_only=True)
class AppointmentUpdated(DomainEvent):
    appointment_id: UUID


@dataclass(frozen=True, kw_only=True)
class AppointmentStatusChanged(DomainEvent):
    appointment_id: UUID
    status: str
