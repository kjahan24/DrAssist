"""Domain events published by ICD-10 Coding module aggregates.

Recorded on an aggregate via `record_event()` and only actually published
(to the `EventBus`) after the transaction that raised them commits
successfully — see `app.shared.application.unit_of_work.UnitOfWork` and
`docs/backend-architecture/10_module_communication.md`.
"""

from dataclasses import dataclass
from uuid import UUID

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class ICD10CodingCreated(DomainEvent):
    icd10_coding_id: UUID
    organization_id: UUID
    clinical_note_id: UUID


@dataclass(frozen=True, kw_only=True)
class ICD10CodingUpdated(DomainEvent):
    icd10_coding_id: UUID
    clinical_note_id: UUID


@dataclass(frozen=True, kw_only=True)
class ICD10CodingPrimaryChanged(DomainEvent):
    icd10_coding_id: UUID
    clinical_note_id: UUID
    primary_code: bool


@dataclass(frozen=True, kw_only=True)
class ICD10CodingReviewStatusChanged(DomainEvent):
    icd10_coding_id: UUID
    clinical_note_id: UUID
    review_status: str
