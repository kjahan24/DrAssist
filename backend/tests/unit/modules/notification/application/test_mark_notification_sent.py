"""Unit tests for the `MarkNotificationSent` use case."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.modules.notification.application.dto import MarkNotificationSentInput
from app.modules.notification.application.use_cases.mark_notification_sent import (
    MarkNotificationSent,
)
from app.modules.notification.domain.entities import Notification
from app.modules.notification.domain.enums import (
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)
from app.modules.notification.domain.exceptions import (
    NotificationExpiredError,
    NotificationNotFoundError,
)
from tests.unit.modules.notification.application.fakes import (
    FakeNotificationRepository,
    FakeUnitOfWork,
)


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


@pytest.fixture
def notification_repository() -> FakeNotificationRepository:
    return FakeNotificationRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    notification_repository: FakeNotificationRepository, unit_of_work: FakeUnitOfWork
) -> MarkNotificationSent:
    return MarkNotificationSent(
        notification_repository=notification_repository, unit_of_work=unit_of_work
    )


class TestMarkNotificationSent:
    async def test_marks_a_pending_notification_sent(
        self, notification_repository: FakeNotificationRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        notification = _make_notification()
        await notification_repository.add(notification)
        use_case = _use_case(notification_repository, unit_of_work)

        output = await use_case.execute(MarkNotificationSentInput(notification_id=notification.id))

        assert output.status is NotificationStatus.SENT

    async def test_unknown_notification_raises(
        self, notification_repository: FakeNotificationRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        use_case = _use_case(notification_repository, unit_of_work)
        with pytest.raises(NotificationNotFoundError):
            await use_case.execute(MarkNotificationSentInput(notification_id=uuid4()))

    async def test_expired_deadline_raises_and_leaves_status_unchanged(
        self, notification_repository: FakeNotificationRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        notification = _make_notification(expires_at=datetime.now(UTC) - timedelta(days=1))
        await notification_repository.add(notification)
        use_case = _use_case(notification_repository, unit_of_work)

        with pytest.raises(NotificationExpiredError):
            await use_case.execute(MarkNotificationSentInput(notification_id=notification.id))

        stored = await notification_repository.get_by_id(notification.id)
        assert stored is not None
        assert stored.status is NotificationStatus.PENDING
