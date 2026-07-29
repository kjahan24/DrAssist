"""Domain events published by Lab Orders module aggregates.

Recorded on an aggregate via `record_event()` and only actually published
(to the `EventBus`) after the transaction that raised them commits
successfully — see `app.shared.application.unit_of_work.UnitOfWork` and
`docs/backend-architecture/10_module_communication.md`.
"""

from dataclasses import dataclass
from uuid import UUID

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class LabOrderCreated(DomainEvent):
    lab_order_id: UUID
    organization_id: UUID
    clinical_note_id: UUID


@dataclass(frozen=True, kw_only=True)
class LabOrderUpdated(DomainEvent):
    lab_order_id: UUID
    clinical_note_id: UUID


@dataclass(frozen=True, kw_only=True)
class LabOrderStatusChanged(DomainEvent):
    lab_order_id: UUID
    clinical_note_id: UUID
    status: str


@dataclass(frozen=True, kw_only=True)
class LabOrderItemAdded(DomainEvent):
    lab_order_item_id: UUID
    lab_order_id: UUID
