"""Unit tests for `NotificationQueryService`."""

from uuid import uuid4

from app.modules.notification.application.services.notification_query_service import (
    NotificationQueryService,
)
from app.modules.notification.domain.entities import Notification
from app.modules.notification.domain.enums import NotificationPriority, NotificationType
from tests.unit.modules.notification.application.fakes import FakeNotificationRepository


def _make_notification(**overrides: object) -> Notification:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "recipient_user_id": uuid4(),
        "notification_type": NotificationType.GENERAL,
        "title": "You have a new message",
        "message": "Please review your latest lab results.",
        "priority": NotificationPriority.NORMAL,
    }
    defaults.update(overrides)
    return Notification.create(**defaults)  # type: ignore[arg-type]


class TestNotificationExists:
    async def test_true_for_a_stored_notification(self) -> None:
        repo = FakeNotificationRepository()
        notification = _make_notification()
        await repo.add(notification)
        service = NotificationQueryService(notification_repository=repo)

        assert await service.notification_exists(notification.id) is True

    async def test_false_for_an_unknown_notification(self) -> None:
        service = NotificationQueryService(notification_repository=FakeNotificationRepository())
        assert await service.notification_exists(uuid4()) is False


class TestGetNotificationSummary:
    async def test_returns_a_summary_for_a_stored_notification(self) -> None:
        repo = FakeNotificationRepository()
        notification = _make_notification()
        await repo.add(notification)
        service = NotificationQueryService(notification_repository=repo)

        summary = await service.get_notification_summary(notification.id)

        assert summary is not None
        assert summary.notification_id == notification.id
        assert summary.title == notification.title

    async def test_returns_none_for_an_unknown_notification(self) -> None:
        service = NotificationQueryService(notification_repository=FakeNotificationRepository())
        assert await service.get_notification_summary(uuid4()) is None


class TestListNotificationsForRecipient:
    async def test_returns_only_that_recipients_notifications(self) -> None:
        repo = FakeNotificationRepository()
        recipient_id = uuid4()
        mine = _make_notification(recipient_user_id=recipient_id)
        other = _make_notification()
        await repo.add(mine)
        await repo.add(other)
        service = NotificationQueryService(notification_repository=repo)

        results = await service.list_notifications_for_recipient(recipient_id)

        assert [r.notification_id for r in results] == [mine.id]

    async def test_returns_empty_list_for_a_recipient_without_notifications(self) -> None:
        service = NotificationQueryService(notification_repository=FakeNotificationRepository())
        assert await service.list_notifications_for_recipient(uuid4()) == []


class TestListUnreadNotificationsForRecipient:
    async def test_only_delivered_notifications_are_unread(self) -> None:
        repo = FakeNotificationRepository()
        recipient_id = uuid4()

        delivered = _make_notification(recipient_user_id=recipient_id)
        delivered.mark_sent()
        delivered.mark_delivered()
        await repo.add(delivered)

        sent_only = _make_notification(recipient_user_id=recipient_id)
        sent_only.mark_sent()
        await repo.add(sent_only)

        read = _make_notification(recipient_user_id=recipient_id)
        read.mark_sent()
        read.mark_delivered()
        read.mark_read()
        await repo.add(read)

        service = NotificationQueryService(notification_repository=repo)
        results = await service.list_unread_notifications_for_recipient(recipient_id)

        assert [r.notification_id for r in results] == [delivered.id]
