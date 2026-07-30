"""`NotificationFacade` — the one concrete implementation of
`NotificationQueryPort`. Constructed per-request (or per background task,
once one exists) by
`app.modules.notification.container.build_notification_facade`, bound to
that caller's `AsyncSession`.
"""

from uuid import UUID

from app.modules.notification.application.services.notification_query_service import (
    NotificationQueryService,
)
from app.modules.notification.public.dto import NotificationSummaryDTO
from app.modules.notification.public.interfaces import NotificationQueryPort


class NotificationFacade(NotificationQueryPort):
    def __init__(self, *, query_service: NotificationQueryService) -> None:
        self._query_service = query_service

    async def notification_exists(self, notification_id: UUID) -> bool:
        return await self._query_service.notification_exists(notification_id)

    async def get_notification_summary(
        self, notification_id: UUID
    ) -> NotificationSummaryDTO | None:
        return await self._query_service.get_notification_summary(notification_id)

    async def list_notifications_for_recipient(
        self, recipient_user_id: UUID
    ) -> list[NotificationSummaryDTO]:
        return await self._query_service.list_notifications_for_recipient(recipient_user_id)

    async def list_unread_notifications_for_recipient(
        self, recipient_user_id: UUID
    ) -> list[NotificationSummaryDTO]:
        return await self._query_service.list_unread_notifications_for_recipient(recipient_user_id)
