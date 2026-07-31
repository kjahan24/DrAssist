"""Module-specific FastAPI dependency providers.

New — this module had no `api/` package before the REST APIs task, so no
`Annotated[..., Depends(...)]`-shaped providers existed either (see
`container.py`'s scope note). Every provider here just adapts
`container.py`'s own session-based `build_<use_case>_use_case` factories
to FastAPI's dependency-injection shape — the exact wiring
`container.py`'s own docstring anticipates ("A future caller — an
`api/dependencies.py` ... calls these factories the same way
`app.modules.appointment.api.dependencies` does today").
"""

from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
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
from app.modules.notification.container import (
    build_cancel_notification_use_case,
    build_create_notification_use_case,
    build_expire_notification_use_case,
    build_mark_notification_delivered_use_case,
    build_mark_notification_read_use_case,
    build_mark_notification_sent_use_case,
)
from app.modules.notification.domain.repositories import NotificationRepository
from app.modules.notification.infrastructure.repositories import (
    SqlAlchemyNotificationRepository,
)


def get_notification_repository(session: DbSession) -> NotificationRepository:
    return SqlAlchemyNotificationRepository(session)


NotificationRepo = Annotated[NotificationRepository, Depends(get_notification_repository)]


def get_notification_query_service(
    notification_repository: NotificationRepo,
) -> NotificationQueryService:
    return NotificationQueryService(notification_repository=notification_repository)


def get_create_notification_use_case(session: DbSession) -> CreateNotification:
    return build_create_notification_use_case(session)


def get_mark_notification_sent_use_case(session: DbSession) -> MarkNotificationSent:
    return build_mark_notification_sent_use_case(session)


def get_mark_notification_delivered_use_case(session: DbSession) -> MarkNotificationDelivered:
    return build_mark_notification_delivered_use_case(session)


def get_mark_notification_read_use_case(session: DbSession) -> MarkNotificationRead:
    return build_mark_notification_read_use_case(session)


def get_cancel_notification_use_case(session: DbSession) -> CancelNotification:
    return build_cancel_notification_use_case(session)


def get_expire_notification_use_case(session: DbSession) -> ExpireNotification:
    return build_expire_notification_use_case(session)
