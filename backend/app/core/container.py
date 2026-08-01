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

    No-op today — several modules publish domain events (e.g.
    `app.modules.authentication.domain.events`), and Patient History,
    Notification, and Audit Log now exist as reactive, event-consuming
    modules per `docs/backend-architecture/03_module_architecture.md`
    (Tier 5), each with its own `container.py` already anticipating this
    wiring — but no module actually calls `subscribe()` here yet, so
    every published event currently reaches zero subscribers. Wiring
    actual subscriptions is deliberately out of scope for the
    Architecture Review & Cleanup task that added this note (it requires
    writing new reactive business logic, not fixing an architecture
    defect) — see
    `docs/backend-architecture/14_doctor_schedule_ownership.md` for the
    review's full findings. Each module adds its subscriptions here once
    that work is undertaken, e.g.:

        from app.modules.notification.container import register_subscriptions
        register_subscriptions(event_bus)
    """
