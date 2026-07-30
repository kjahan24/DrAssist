"""Unit tests for the `MarkNotificationDelivered` use case."""

from uuid import uuid4

import pytest

from app.modules.notification.application.dto import MarkNotificationDeliveredInput
from app.modules.notification.application.use_cases.mark_notification_delivered import (
    MarkNotificationDelivered,
)
from app.modules.notification.domain.entities import Notification
from app.modules.notification.domain.enums import (
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)
from app.modules.notification.domain.exceptions import (
    InvalidNotificationStatusTransitionError,
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
) -> MarkNotificationDelivered:
    return MarkNotificationDelivered(
        notification_repository=notification_repository, unit_of_work=unit_of_work
    )


class TestMarkNotificationDelivered:
    async def test_marks_a_sent_notification_delivered(
        self, notification_repository: FakeNotificationRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        notification = _make_notification()
        notification.mark_sent()
        await notification_repository.add(notification)
        use_case = _use_case(notification_repository, unit_of_work)

        output = await use_case.execute(
            MarkNotificationDeliveredInput(notification_id=notification.id)
        )

        assert output.status is NotificationStatus.DELIVERED

    async def test_unknown_notification_raises(
        self, notification_repository: FakeNotificationRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        use_case = _use_case(notification_repository, unit_of_work)
        with pytest.raises(NotificationNotFoundError):
            await use_case.execute(MarkNotificationDeliveredInput(notification_id=uuid4()))

    async def test_pending_notification_cannot_be_marked_delivered(
        self, notification_repository: FakeNotificationRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        notification = _make_notification()
        await notification_repository.add(notification)
        use_case = _use_case(notification_repository, unit_of_work)

        with pytest.raises(InvalidNotificationStatusTransitionError):
            await use_case.execute(MarkNotificationDeliveredInput(notification_id=notification.id))
