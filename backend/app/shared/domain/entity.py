"""Base classes for domain entities and aggregate roots.

Plain Python dataclasses with identity — no framework imports. Every
module's `domain/entities.py` builds on `Entity` (has identity, no event
collection) or `AggregateRoot` (has identity, timestamps, and collects
domain events raised by its own methods until a Unit of Work pulls them
after a successful commit). See
`docs/backend-architecture/00_architectural_principles.md §2` and
`§7 (Unit of Work)`.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.shared.domain.domain_event import DomainEvent


@dataclass(kw_only=True, eq=False)
class Entity:
    """`eq=False` on every entity dataclass in this hierarchy is deliberate.

    Entities have identity-based equality (two `User` instances with the
    same `id` are "the same user" even if every other field differs) —
    the opposite of a dataclass's default *structural* equality (compare
    all fields). `eq=False` stops `@dataclass` from generating its own
    `__eq__`/`__hash__` on *every subclass* (it would otherwise do so
    again at each level of the hierarchy, since it only skips generation
    when a method already exists on that exact class's own `__dict__`,
    not on an inherited base) so every entity — this class and every
    concrete aggregate — shares the identity-based `__eq__`/`__hash__`
    defined once, below. Every module's concrete entity dataclasses must
    also pass `eq=False` for the same reason.
    """

    id: UUID = field(default_factory=uuid4)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return NotImplemented
        return type(self) is type(other) and self.id == other.id

    def __hash__(self) -> int:
        return hash((type(self), self.id))


@dataclass(kw_only=True, eq=False)
class AggregateRoot(Entity):
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    _domain_events: list[DomainEvent] = field(
        default_factory=list, repr=False, compare=False, hash=False
    )

    def record_event(self, event: DomainEvent) -> None:
        """Append a domain event, to be published only after a successful commit."""
        self._domain_events.append(event)

    def pull_events(self) -> list[DomainEvent]:
        """Drain and return every event recorded since the last pull."""
        events = list(self._domain_events)
        self._domain_events.clear()
        return events

    def touch(self) -> None:
        """Refresh `updated_at`. Call from mutating methods that don't already do so."""
        self.updated_at = datetime.now(UTC)
