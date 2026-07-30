"""Integration tests for `SqlAlchemyNotificationRepository`, including the
FKs to `organizations`/`users`, the JSONB `metadata` round trip, and the
`scheduled_at <= expires_at` `CHECK` constraint, against a real
PostgreSQL instance.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.notification._helpers import (
    persist_organization_and_user,
    persist_user,
)

from app.modules.notification.domain.entities import Notification
from app.modules.notification.domain.enums import (
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)
from app.modules.notification.infrastructure.models import NotificationModel
from app.modules.notification.infrastructure.repositories import SqlAlchemyNotificationRepository

_FUTURE = datetime.now(UTC) + timedelta(days=1)


class TestNotificationRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, recipient = await persist_organization_and_user(db_session)
        repo = SqlAlchemyNotificationRepository(db_session)

        notification = Notification.create(
            organization_id=organization.id,
            recipient_user_id=recipient.id,
            notification_type=NotificationType.LAB_RESULT_READY,
            title="Your lab results are ready",
            message="Log in to view your latest lab results.",
            priority=NotificationPriority.HIGH,
        )
        await repo.add(notification)
        await db_session.commit()

        reloaded = await repo.get_by_id(notification.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.recipient_user_id == recipient.id
        assert reloaded.notification_type is NotificationType.LAB_RESULT_READY
        assert reloaded.title == "Your lab results are ready"
        assert reloaded.priority is NotificationPriority.HIGH
        assert reloaded.status is NotificationStatus.PENDING
        assert reloaded.reference_type is None
        assert reloaded.reference_id is None
        assert reloaded.metadata is None

    async def test_save_with_reference_and_metadata_preserves_them(
        self, db_session: AsyncSession
    ) -> None:
        organization, recipient = await persist_organization_and_user(db_session)
        repo = SqlAlchemyNotificationRepository(db_session)
        reference_id = uuid4()

        notification = Notification.create(
            organization_id=organization.id,
            recipient_user_id=recipient.id,
            notification_type=NotificationType.APPOINTMENT_REMINDER,
            title="Upcoming appointment",
            message="You have an appointment tomorrow at 9am.",
            priority=NotificationPriority.NORMAL,
            reference_type="appointment",
            reference_id=reference_id,
            scheduled_at=_FUTURE,
            expires_at=_FUTURE + timedelta(days=1),
            metadata={"channel_hint": "in_app", "retry_count": 0},
        )
        await repo.add(notification)
        await db_session.commit()

        reloaded = await repo.get_by_id(notification.id)
        assert reloaded is not None
        assert reloaded.reference_type == "appointment"
        assert reloaded.reference_id == reference_id
        assert reloaded.status is NotificationStatus.SCHEDULED
        assert reloaded.metadata == {"channel_hint": "in_app", "retry_count": 0}

    async def test_full_workflow_persists(self, db_session: AsyncSession) -> None:
        organization, recipient = await persist_organization_and_user(db_session)
        repo = SqlAlchemyNotificationRepository(db_session)

        notification = Notification.create(
            organization_id=organization.id,
            recipient_user_id=recipient.id,
            notification_type=NotificationType.GENERAL,
            title="You have a new message",
            message="Please review your latest lab results.",
            priority=NotificationPriority.NORMAL,
        )
        await repo.add(notification)
        await db_session.commit()

        notification.mark_sent()
        await repo.add(notification)
        await db_session.commit()

        notification.mark_delivered()
        await repo.add(notification)
        await db_session.commit()

        notification.mark_read()
        await repo.add(notification)
        await db_session.commit()

        reloaded = await repo.get_by_id(notification.id)
        assert reloaded is not None
        assert reloaded.status is NotificationStatus.READ
        assert reloaded.sent_at is not None
        assert reloaded.read_at is not None


class TestListByRecipient:
    async def test_list_by_recipient_returns_only_that_recipients_notifications(
        self, db_session: AsyncSession
    ) -> None:
        organization, recipient = await persist_organization_and_user(db_session)
        other_recipient = await persist_user(db_session, organization_id=organization.id)
        repo = SqlAlchemyNotificationRepository(db_session)

        mine = Notification.create(
            organization_id=organization.id,
            recipient_user_id=recipient.id,
            notification_type=NotificationType.GENERAL,
            title="For me",
            message="This one is for me.",
            priority=NotificationPriority.NORMAL,
        )
        other = Notification.create(
            organization_id=organization.id,
            recipient_user_id=other_recipient.id,
            notification_type=NotificationType.GENERAL,
            title="For someone else",
            message="This one is not for me.",
            priority=NotificationPriority.NORMAL,
        )
        await repo.add(mine)
        await repo.add(other)
        await db_session.commit()

        results = await repo.list_by_recipient(recipient.id)
        assert [n.id for n in results] == [mine.id]

    async def test_returns_empty_list_for_a_recipient_without_notifications(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyNotificationRepository(db_session)
        assert await repo.list_by_recipient(uuid4()) == []


class TestListUnreadByRecipient:
    async def test_only_delivered_notifications_are_unread(self, db_session: AsyncSession) -> None:
        organization, recipient = await persist_organization_and_user(db_session)
        repo = SqlAlchemyNotificationRepository(db_session)

        delivered = Notification.create(
            organization_id=organization.id,
            recipient_user_id=recipient.id,
            notification_type=NotificationType.GENERAL,
            title="Delivered",
            message="This one was delivered.",
            priority=NotificationPriority.NORMAL,
        )
        delivered.mark_sent()
        delivered.mark_delivered()

        pending = Notification.create(
            organization_id=organization.id,
            recipient_user_id=recipient.id,
            notification_type=NotificationType.GENERAL,
            title="Pending",
            message="This one is still pending.",
            priority=NotificationPriority.NORMAL,
        )

        await repo.add(delivered)
        await repo.add(pending)
        await db_session.commit()

        results = await repo.list_unread_by_recipient(recipient.id)
        assert [n.id for n in results] == [delivered.id]


class TestNotificationRequiresValidReferences:
    async def test_nonexistent_organization_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        _organization, recipient = await persist_organization_and_user(db_session)
        repo = SqlAlchemyNotificationRepository(db_session)

        notification = Notification.create(
            organization_id=uuid4(),
            recipient_user_id=recipient.id,
            notification_type=NotificationType.GENERAL,
            title="Orphan organization",
            message="This references a nonexistent organization.",
            priority=NotificationPriority.NORMAL,
        )
        await repo.add(notification)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_recipient_user_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _recipient = await persist_organization_and_user(db_session)
        repo = SqlAlchemyNotificationRepository(db_session)

        notification = Notification.create(
            organization_id=organization.id,
            recipient_user_id=uuid4(),
            notification_type=NotificationType.GENERAL,
            title="Orphan recipient",
            message="This references a nonexistent recipient.",
            priority=NotificationPriority.NORMAL,
        )
        await repo.add(notification)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestCheckConstraints:
    """`Notification.__post_init__` already prevents `scheduled_at` from
    ever being later than `expires_at` via the domain layer — this test
    targets the DB `CHECK` constraint directly (bypassing the domain
    entity, the way a direct SQL edit would) to prove the
    defense-in-depth layer actually works, the same pattern
    `tests.integration.modules.appointment.test_appointment_repository
    .TestCheckConstraints` already established.
    """

    async def test_scheduled_at_after_expires_at_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, recipient = await persist_organization_and_user(db_session)

        model = NotificationModel(
            organization_id=organization.id,
            recipient_user_id=recipient.id,
            notification_type=NotificationType.GENERAL,
            title="Invalid schedule",
            message="This bypasses the domain layer.",
            priority=NotificationPriority.NORMAL,
            status=NotificationStatus.SCHEDULED,
            scheduled_at=datetime(2026, 6, 10, tzinfo=UTC),
            expires_at=datetime(2026, 6, 1, tzinfo=UTC),
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
