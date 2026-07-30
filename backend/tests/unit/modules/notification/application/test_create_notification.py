"""Unit tests for the `CreateNotification` use case, using in-memory
fakes for this module's own repository and the Authentication module's
public port (via `NotificationConsistencyService`)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.modules.notification.application.dto import CreateNotificationInput
from app.modules.notification.application.services.notification_consistency_service import (
    NotificationConsistencyService,
)
from app.modules.notification.application.use_cases.create_notification import CreateNotification
from app.modules.notification.domain.enums import (
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)
from app.modules.notification.domain.events import NotificationCreated
from app.modules.notification.domain.exceptions import RecipientNotFoundError
from tests.unit.modules.notification.application.fakes import (
    FakeNotificationRepository,
    FakeUnitOfWork,
    FakeUserQueryPort,
    make_user_summary,
)


def _make_input(**overrides: object) -> CreateNotificationInput:
    defaults: dict[str, object] = {
        "recipient_user_id": uuid4(),
        "notification_type": NotificationType.GENERAL,
        "title": "You have a new message",
        "message": "Please review your latest lab results.",
        "priority": NotificationPriority.NORMAL,
    }
    defaults.update(overrides)
    return CreateNotificationInput(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def notification_repository() -> FakeNotificationRepository:
    return FakeNotificationRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    notification_repository: FakeNotificationRepository,
    unit_of_work: FakeUnitOfWork,
    user_query_port: FakeUserQueryPort,
) -> CreateNotification:
    return CreateNotification(
        notification_repository=notification_repository,
        consistency_service=NotificationConsistencyService(user_query_port=user_query_port),
        unit_of_work=unit_of_work,
    )


class TestCreateNotification:
    async def test_creates_notification_with_derived_organization_id(
        self, notification_repository: FakeNotificationRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        organization_id = uuid4()
        recipient_user_id = uuid4()
        user_port = FakeUserQueryPort(
            existing_users={
                recipient_user_id: make_user_summary(
                    user_id=recipient_user_id, organization_id=organization_id
                )
            }
        )
        use_case = _use_case(notification_repository, unit_of_work, user_port)

        output = await use_case.execute(_make_input(recipient_user_id=recipient_user_id))

        assert output.organization_id == organization_id
        assert output.status is NotificationStatus.PENDING
        stored = await notification_repository.get_by_id(output.notification_id)
        assert stored is not None
        assert stored.recipient_user_id == recipient_user_id
        assert unit_of_work.committed is True
        assert any(isinstance(e, NotificationCreated) for e in unit_of_work.published_events)

    async def test_unknown_recipient_raises(
        self, notification_repository: FakeNotificationRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        use_case = _use_case(notification_repository, unit_of_work, FakeUserQueryPort())
        with pytest.raises(RecipientNotFoundError):
            await use_case.execute(_make_input())

    async def test_with_scheduled_at_starts_scheduled(
        self, notification_repository: FakeNotificationRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        recipient_user_id = uuid4()
        user_port = FakeUserQueryPort(
            existing_users={recipient_user_id: make_user_summary(user_id=recipient_user_id)}
        )
        use_case = _use_case(notification_repository, unit_of_work, user_port)

        output = await use_case.execute(
            _make_input(
                recipient_user_id=recipient_user_id,
                scheduled_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )

        assert output.status is NotificationStatus.SCHEDULED

    async def test_reference_pair_is_preserved(
        self, notification_repository: FakeNotificationRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        recipient_user_id = uuid4()
        reference_id = uuid4()
        user_port = FakeUserQueryPort(
            existing_users={recipient_user_id: make_user_summary(user_id=recipient_user_id)}
        )
        use_case = _use_case(notification_repository, unit_of_work, user_port)

        output = await use_case.execute(
            _make_input(
                recipient_user_id=recipient_user_id,
                reference_type="appointment",
                reference_id=reference_id,
            )
        )

        stored = await notification_repository.get_by_id(output.notification_id)
        assert stored is not None
        assert stored.reference_type == "appointment"
        assert stored.reference_id == reference_id
