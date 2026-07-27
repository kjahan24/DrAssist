"""App-wide composition root.

Process-lifetime singletons that don't belong to any one module — today,
just the `EventBus`. Built once in `app/main.py`'s `lifespan`, retrieved
via `get_event_bus()` (an `lru_cache`d provider, the same pattern
`app.core.config.get_settings` already uses) rather than a module-level
global, so tests can construct an isolated instance instead of sharing
process state.

As more modules are added, each registers its event subscriptions here
via `configure_event_subscriptions` — this file is where the "who
subscribes to what" wiring lives, per
`docs/backend-architecture/10_module_communication.md`; a publishing
module never imports its subscribers directly.
"""

from functools import lru_cache

from app.shared.application.event_bus import EventBus
from app.shared.infrastructure.in_process_event_bus import InProcessEventBus


@lru_cache
def get_event_bus() -> EventBus:
    return InProcessEventBus()


def configure_event_subscriptions(event_bus: EventBus) -> None:
    """Register every module's event subscriptions.

    No-op today — the Authentication module publishes events
    (`app.modules.authentication.domain.events`) but no other module
    exists yet to subscribe to them (Patient History, Notification, and
    Audit are future modules per
    `docs/backend-architecture/03_module_architecture.md`). Each future
    module adds its subscriptions here, e.g.:

        from app.modules.notification.container import register_subscriptions
        register_subscriptions(event_bus)
    """
