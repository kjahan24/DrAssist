"""Domain events published by Lab Results module aggregates.

Recorded on an aggregate via `record_event()` and only actually published
(to the `EventBus`) after the transaction that raised them commits
successfully — see `app.shared.application.unit_of_work.UnitOfWork` and
`docs/backend-architecture/10_module_communication.md`.
"""

from dataclasses import dataclass
from uuid import UUID

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class LabResultCreated(DomainEvent):
    lab_result_id: UUID
    organization_id: UUID
    lab_order_id: UUID


@dataclass(frozen=True, kw_only=True)
class LabResultUpdated(DomainEvent):
    lab_result_id: UUID
    lab_order_id: UUID


@dataclass(frozen=True, kw_only=True)
class LabResultFinalized(DomainEvent):
    lab_result_id: UUID
    lab_order_id: UUID


@dataclass(frozen=True, kw_only=True)
class LabResultItemAdded(DomainEvent):
    lab_result_item_id: UUID
    lab_result_id: UUID
