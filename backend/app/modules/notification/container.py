"""Module composition root.

Every prior module splits its composition root in two: `container.py`
builds the read-only public facade (`build_<module>_facade`), while
`api/dependencies.py` builds the write-side use cases as FastAPI
`Depends()` providers, bound to a request-scoped `AsyncSession` and
`SqlAlchemyUnitOfWork` (see e.g.
`app.modules.appointment.api.dependencies`). This task explicitly
excludes API endpoints ("Do NOT implement API endpoints"), so this
module has no `api/` package at all, and therefore nowhere else to put
the write-side wiring. `container.py` builds both here instead:
`build_notification_facade` (the read-only public port, matching every
prior module exactly) and one `build_<use_case>_use_case` factory per
use case, each taking `session` and returning a ready-to-`execute()`
instance bound to a `SqlAlchemyUnitOfWork` for that same session — the
same construction `api/dependencies.py`'s own provider functions do
elsewhere, minus the FastAPI-specific `Annotated[..., Depends(...)]`
wiring, which has no meaning without an API layer.

A future caller — an `api/dependencies.py` once HTTP endpoints are
built, a Background Job, or an event subscriber registered via
`app.core.container.configure_event_subscriptions` (that file's own
docstring already anticipates a future
`app.modules.notification.container.register_subscriptions` — not built
by this task, since neither event subscriptions nor Background Jobs are
in this task's Implement checklist) — calls these factories the same way
`app.modules.appointment.api.dependencies` calls
`app.modules.appointment.container.build_appointment_facade` today.

Scope note — this task builds the Notification module's **foundation**
only: the `Notification` aggregate (`domain/entities.py`), its
repository, `CreateNotification` (derives `organization_id` from the
recipient `User` via `NotificationConsistencyService` — see
`application/services/notification_consistency_service.py` for why
`reference_type`/`reference_id` are *not* cross-module-validated),
`MarkNotificationSent`, `MarkNotificationDelivered`,
`MarkNotificationRead`, `CancelNotification`, `ExpireNotification`
(together enforcing "valid status transitions" via an explicit
transition map — see `domain/entities.py`), and the public read-only
query facade.

This module deliberately does **not** implement Email delivery, SMS
delivery, Push notification delivery, WebSocket, any HTTP endpoint, or
any Background Job (per this task's explicit exclusions), and does not
modify the Authentication, Organization, Doctor, Patient, Appointment,
Schedule, or Visit modules or their tables — it only *reads*
Authentication through its public port (`UserQueryPort`), to
resolve/validate the recipient and derive `organization_id`.

Email, SMS, Push Notifications, WebSocket, Background Jobs, Mobile Apps,
Family/Caregiver Access, and an AI Reminder System are explicitly out of
scope for this task — they are expected to become their own modules (or
delivery-channel integrations), each depending on `NotificationQueryPort`
(keyed by `notification_id`, or
`list_notifications_for_recipient`/`list_unread_notifications_for_recipient`
for the recipient-scoped views) the same way this module itself depends
on Authentication's own port. Nothing about this schema needs to change
to support them: `status` already gives a future delivery-channel worker
the state machine to react to via `NotificationStatusChanged`, and
`metadata` (JSONB) already gives a future AI Reminder System or
delivery-channel integration a place to carry channel-specific payloads
without a schema change.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.container import get_event_bus
from app.modules.authentication.container import build_authentication_facade
from app.modules.authentication.public.interfaces import UserQueryPort
from app.modules.notification.application.services.notification_consistency_service import (
    NotificationConsistencyService,
)
from app.modules.notification.application.services.notification_query_service import (
    NotificationQueryService,
)
from app.modules.notification.application.use_cases.cancel_notification import CancelNotification
from app.modules.notification.application.use_cases.create_notification import CreateNotification
from app.modules.notification.application.use_cases.expire_notification import ExpireNotification
from app.modules.notification.application.use_cases.mark_notification_delivered import (
    MarkNotificationDelivered,
)
from app.modules.notification.application.use_cases.mark_notification_read import (
    MarkNotificationRead,
)
from app.modules.notification.application.use_cases.mark_notification_sent import (
    MarkNotificationSent,
)
from app.modules.notification.infrastructure.repositories import SqlAlchemyNotificationRepository
from app.modules.notification.public.facade import NotificationFacade
from app.shared.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def build_notification_facade(session: AsyncSession) -> NotificationFacade:
    """Construct a `NotificationFacade` wired to `session`.

    Called once per request (or per Celery task) — every repository it
    builds shares `session`, so it participates in the same transaction
    as the rest of that request's work.
    """
    notification_repository = SqlAlchemyNotificationRepository(session)
    query_service = NotificationQueryService(notification_repository=notification_repository)
    return NotificationFacade(query_service=query_service)


def build_user_query_port(session: AsyncSession) -> UserQueryPort:
    return build_authentication_facade(session)


def build_create_notification_use_case(session: AsyncSession) -> CreateNotification:
    notification_repository = SqlAlchemyNotificationRepository(session)
    consistency_service = NotificationConsistencyService(
        user_query_port=build_user_query_port(session)
    )
    unit_of_work = SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())
    return CreateNotification(
        notification_repository=notification_repository,
        consistency_service=consistency_service,
        unit_of_work=unit_of_work,
    )


def build_mark_notification_sent_use_case(session: AsyncSession) -> MarkNotificationSent:
    notification_repository = SqlAlchemyNotificationRepository(session)
    unit_of_work = SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())
    return MarkNotificationSent(
        notification_repository=notification_repository, unit_of_work=unit_of_work
    )


def build_mark_notification_delivered_use_case(session: AsyncSession) -> MarkNotificationDelivered:
    notification_repository = SqlAlchemyNotificationRepository(session)
    unit_of_work = SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())
    return MarkNotificationDelivered(
        notification_repository=notification_repository, unit_of_work=unit_of_work
    )


def build_mark_notification_read_use_case(session: AsyncSession) -> MarkNotificationRead:
    notification_repository = SqlAlchemyNotificationRepository(session)
    unit_of_work = SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())
    return MarkNotificationRead(
        notification_repository=notification_repository, unit_of_work=unit_of_work
    )


def build_cancel_notification_use_case(session: AsyncSession) -> CancelNotification:
    notification_repository = SqlAlchemyNotificationRepository(session)
    unit_of_work = SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())
    return CancelNotification(
        notification_repository=notification_repository, unit_of_work=unit_of_work
    )


def build_expire_notification_use_case(session: AsyncSession) -> ExpireNotification:
    notification_repository = SqlAlchemyNotificationRepository(session)
    unit_of_work = SqlAlchemyUnitOfWork(session, event_bus=get_event_bus())
    return ExpireNotification(
        notification_repository=notification_repository, unit_of_work=unit_of_work
    )
