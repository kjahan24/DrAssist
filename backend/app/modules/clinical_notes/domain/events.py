"""Domain events published by Clinical Notes module aggregates.

Recorded on an aggregate via `record_event()` and only actually published
(to the `EventBus`) after the transaction that raised them commits
successfully — see `app.shared.application.unit_of_work.UnitOfWork` and
`docs/backend-architecture/10_module_communication.md`.
"""

from dataclasses import dataclass
from uuid import UUID

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class ClinicalNoteCreated(DomainEvent):
    clinical_note_id: UUID
    organization_id: UUID
    patient_id: UUID
    visit_id: UUID
    note_number: str


@dataclass(frozen=True, kw_only=True)
class ClinicalNoteUpdated(DomainEvent):
    clinical_note_id: UUID
    visit_id: UUID


@dataclass(frozen=True, kw_only=True)
class ClinicalNoteStatusChanged(DomainEvent):
    clinical_note_id: UUID
    visit_id: UUID
    status: str
