"""Domain events published by Prescription module aggregates.

Recorded on an aggregate via `record_event()` and only actually published
(to the `EventBus`) after the transaction that raised them commits
successfully — see `app.shared.application.unit_of_work.UnitOfWork` and
`docs/backend-architecture/10_module_communication.md`.
"""

from dataclasses import dataclass
from uuid import UUID

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class PrescriptionCreated(DomainEvent):
    prescription_id: UUID
    organization_id: UUID
    clinical_note_id: UUID


@dataclass(frozen=True, kw_only=True)
class PrescriptionUpdated(DomainEvent):
    prescription_id: UUID
    clinical_note_id: UUID


@dataclass(frozen=True, kw_only=True)
class PrescriptionFinalized(DomainEvent):
    prescription_id: UUID
    clinical_note_id: UUID


@dataclass(frozen=True, kw_only=True)
class PrescriptionItemAdded(DomainEvent):
    prescription_item_id: UUID
    prescription_id: UUID
