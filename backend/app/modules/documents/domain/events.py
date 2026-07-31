"""Domain events published by Documents module aggregates.

Recorded on an aggregate via `record_event()` and only actually published
(to the `EventBus`) after the transaction that raised them commits
successfully — see `app.shared.application.unit_of_work.UnitOfWork` and
`docs/backend-architecture/10_module_communication.md`. Shaped like
`app.modules.clinical_notes.domain.events` (`Created`/`StatusChanged`/
`Updated` — one generic status-change event rather than one per
transition), the closest precedent for an aggregate with more than two
lifecycle states.
"""

from dataclasses import dataclass
from uuid import UUID

from app.modules.documents.domain.enums import DocumentStatus
from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class MedicalDocumentUploaded(DomainEvent):
    document_id: UUID
    organization_id: UUID
    patient_id: UUID
    stored_filename: str


@dataclass(frozen=True, kw_only=True)
class MedicalDocumentStatusChanged(DomainEvent):
    document_id: UUID
    old_status: DocumentStatus
    new_status: DocumentStatus


@dataclass(frozen=True, kw_only=True)
class MedicalDocumentUpdated(DomainEvent):
    document_id: UUID
