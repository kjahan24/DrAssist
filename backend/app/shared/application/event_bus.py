"""Event Bus interface.

A module publishes domain events without knowing who, if anyone,
subscribes; subscriptions are registered centrally at the composition
root, never by the publishing module importing the subscriber. See
`docs/backend-architecture/10_module_communication.md`.
"""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Sequence

from app.shared.domain.domain_event import DomainEvent

EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventBus(ABC):
    @abstractmethod
    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        """Register `handler` to run whenever an event of `event_type` is published."""
        ...

    @abstractmethod
    async def publish(self, events: Sequence[DomainEvent]) -> None:
        """Dispatch each event to every handler registered for its exact type."""
        ...
