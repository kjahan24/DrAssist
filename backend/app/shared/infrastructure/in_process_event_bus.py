"""In-process Event Bus — the one concrete `EventBus` implementation today.

Swapping this for a real broker (RabbitMQ/Kafka/SNS-SQS) at microservices-
extraction time is an infrastructure-only change: every publisher and
subscriber depends on `EventBus`, never on this class. See
`docs/backend-architecture/13_microservices_migration_path.md`.
"""

from collections import defaultdict
from collections.abc import Sequence

from app.core.logging import get_logger
from app.shared.application.event_bus import EventBus, EventHandler
from app.shared.domain.domain_event import DomainEvent

logger = get_logger(__name__)


class InProcessEventBus(EventBus):
    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, events: Sequence[DomainEvent]) -> None:
        for event in events:
            handlers = self._handlers.get(type(event), [])
            for handler in handlers:
                # A subscriber's own failure must never corrupt another
                # subscriber's turn or mask the fact that the triggering
                # transaction already committed successfully.
                try:
                    await handler(event)
                except Exception:
                    logger.error(
                        "event_handler_failed",
                        event_type=type(event).__name__,
                        event_id=str(event.event_id),
                        handler=getattr(handler, "__qualname__", repr(handler)),
                        exc_info=True,
                    )
