"""Domain events published by Attachments module aggregates.

Recorded on an aggregate via `record_event()` and only actually published
(to the `EventBus`) after the transaction that raised them commits
successfully — see `app.shared.application.unit_of_work.UnitOfWork` and
`docs/backend-architecture/10_module_communication.md`.
"""

from dataclasses import dataclass
from uuid import UUID

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class VisitAttachmentUploaded(DomainEvent):
    attachment_id: UUID
    organization_id: UUID
    visit_id: UUID
    storage_key: str


@dataclass(frozen=True, kw_only=True)
class VisitAttachmentUpdated(DomainEvent):
    attachment_id: UUID
    visit_id: UUID
