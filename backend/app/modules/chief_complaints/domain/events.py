"""Domain events published by Chief Complaints module aggregates.

Recorded on an aggregate via `record_event()` and only actually published
(to the `EventBus`) after the transaction that raised them commits
successfully — see `app.shared.application.unit_of_work.UnitOfWork` and
`docs/backend-architecture/10_module_communication.md`.
"""

from dataclasses import dataclass
from uuid import UUID

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class VisitChiefComplaintRecorded(DomainEvent):
    chief_complaint_id: UUID
    organization_id: UUID
    visit_id: UUID
    sequence_number: int


@dataclass(frozen=True, kw_only=True)
class VisitChiefComplaintUpdated(DomainEvent):
    chief_complaint_id: UUID
    visit_id: UUID
