"""Domain events published by Patient History module aggregates.

Recorded on an aggregate via `record_event()` and only actually published
(to the `EventBus`) after the transaction that raised them commits
successfully — see `app.shared.application.unit_of_work.UnitOfWork` and
`docs/backend-architecture/10_module_communication.md`.

There is no `PatientHistoryUpdated`/`PatientHistoryDeleted` event: "History
records are immutable" / "append-only" — no method on `PatientHistory`
ever mutates a record after `create()`, so no other event type could ever
be recorded.
"""

from dataclasses import dataclass
from uuid import UUID

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class PatientHistoryCreated(DomainEvent):
    patient_history_id: UUID
    organization_id: UUID
    patient_id: UUID
    reference_type: str
    reference_id: UUID
