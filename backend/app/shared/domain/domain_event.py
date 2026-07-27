"""Base type for domain events.

A domain event is an immutable record of something that already happened
inside an aggregate. Concrete events (e.g. `UserRegistered`) subclass this
with their own frozen fields. Events are recorded on an `AggregateRoot`
via `record_event()` and collected by the Unit of Work after a successful
commit, then handed to the `EventBus` — see
`app/shared/application/unit_of_work.py` and
`docs/backend-architecture/10_module_communication.md`.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
