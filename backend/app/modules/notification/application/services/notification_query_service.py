"""Read-only queries against `Notification`.

Backs the module's public `NotificationQueryPort` — the one
implementation, per
`docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).

`list_notifications_for_recipient`/`list_unread_notifications_for_recipient`
are the natural read axes for a future notification-inbox consumer
(Mobile Apps, a future HTTP endpoint, Patient Portal) — the same shape
every prior module's query service exposes for each of its own real FK
parents. "Unread" means `status == Delivered`: a notification that has
reached the recipient (delivery confirmed) but has not yet been marked
`Read`. `Sent`-but-not-yet-`Delivered` notifications are not counted —
delivery hasn't been confirmed yet — and `Read`/`Cancelled`/`Expired`
notifications are resolved states, not unread ones.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.notification.application.dto import NotificationSummaryDTO
from app.modules.notification.domain.entities import Notification
from app.modules.notification.domain.enums import NotificationPriority, NotificationStatus
from app.modules.notification.domain.repositories import NotificationRepository


class NotificationQueryService:
    def __init__(self, *, notification_repository: NotificationRepository) -> None:
        self._notifications = notification_repository

    async def notification_exists(self, notification_id: UUID) -> bool:
        return await self._notifications.get_by_id(notification_id) is not None

    async def get_notification_summary(
        self, notification_id: UUID
    ) -> NotificationSummaryDTO | None:
        notification = await self._notifications.get_by_id(notification_id)
        return _to_summary(notification) if notification is not None else None

    async def list_notifications_for_recipient(
        self, recipient_user_id: UUID
    ) -> list[NotificationSummaryDTO]:
        notifications = await self._notifications.list_by_recipient(recipient_user_id)
        return [_to_summary(notification) for notification in notifications]

    async def list_unread_notifications_for_recipient(
        self, recipient_user_id: UUID
    ) -> list[NotificationSummaryDTO]:
        notifications = await self._notifications.list_unread_by_recipient(recipient_user_id)
        return [_to_summary(notification) for notification in notifications]

    async def search_notifications(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        statuses: Sequence[NotificationStatus] | None = None,
        priorities: Sequence[NotificationPriority] | None = None,
        recipient_user_id: UUID | None = None,
        reference_type: str | None = None,
        reference_id: UUID | None = None,
        scheduled_from: datetime | None = None,
        scheduled_to: datetime | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "desc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[NotificationSummaryDTO], int]:
        """Search & Filtering module — see `NotificationRepository.search`'s
        docstring for filter/sort/pagination semantics."""
        notifications, total = await self._notifications.search(
            organization_id=organization_id,
            query=query,
            statuses=statuses,
            priorities=priorities,
            recipient_user_id=recipient_user_id,
            reference_type=reference_type,
            reference_id=reference_id,
            scheduled_from=scheduled_from,
            scheduled_to=scheduled_to,
            created_from=created_from,
            created_to=created_to,
            updated_from=updated_from,
            updated_to=updated_to,
            include_deleted=include_deleted,
            sort_by=sort_by,
            sort_order=sort_order,
            offset=offset,
            limit=limit,
        )
        return [_to_summary(notification) for notification in notifications], total


def _to_summary(notification: Notification) -> NotificationSummaryDTO:
    return NotificationSummaryDTO(
        notification_id=notification.id,
        organization_id=notification.organization_id,
        recipient_user_id=notification.recipient_user_id,
        notification_type=notification.notification_type,
        title=notification.title,
        message=notification.message,
        priority=notification.priority,
        status=notification.status,
        reference_type=notification.reference_type,
        reference_id=notification.reference_id,
        scheduled_at=notification.scheduled_at,
        sent_at=notification.sent_at,
        read_at=notification.read_at,
        expires_at=notification.expires_at,
        metadata=notification.metadata,
    )
