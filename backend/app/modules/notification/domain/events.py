"""Domain events published by Notification module aggregates.

Recorded on an aggregate via `record_event()` and only actually published
(to the `EventBus`) after the transaction that raised them commits
successfully — see `app.shared.application.unit_of_work.UnitOfWork` and
`docs/backend-architecture/10_module_communication.md`.

One generic `NotificationStatusChanged` event backs every transition
(`mark_sent()`/`mark_delivered()`/`mark_read()`/`cancel()`/
`mark_expired()`) rather than a distinct event per action — the same
minimal shape `app.modules.appointment.domain.events
.AppointmentStatusChanged` already establishes for its own multi-action
transition set. `app.core.container.configure_event_subscriptions`
already anticipates a future subscriber module registering against
events like these (see that file's own docstring) — no subscriber exists
yet, so nothing beyond recording/publishing the event is implemented
here.
"""

from dataclasses import dataclass
from uuid import UUID

from app.shared.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class NotificationCreated(DomainEvent):
    notification_id: UUID
    organization_id: UUID
    recipient_user_id: UUID
    notification_type: str


@dataclass(frozen=True, kw_only=True)
class NotificationStatusChanged(DomainEvent):
    notification_id: UUID
    status: str
