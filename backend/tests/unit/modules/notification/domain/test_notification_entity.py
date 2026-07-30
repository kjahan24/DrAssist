"""Unit tests for the `Notification` aggregate's own invariants: starting
status derived from `scheduled_at`, blank `title`/`message` rejection,
the "both set or both omitted" `reference_type`/`reference_id` pairing,
"scheduled_at must not be after expires_at", the explicit
status-transition map, and the `mark_sent()` expiry guard."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.modules.notification.domain.entities import Notification
from app.modules.notification.domain.enums import (
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)
from app.modules.notification.domain.events import NotificationCreated, NotificationStatusChanged
from app.modules.notification.domain.exceptions import (
    InvalidNotificationReferenceError,
    InvalidNotificationScheduleError,
    InvalidNotificationStatusTransitionError,
    NotificationExpiredError,
    NotificationMessageRequiredError,
    NotificationTitleRequiredError,
)

_FUTURE = datetime.now(UTC) + timedelta(days=1)
_PAST = datetime.now(UTC) - timedelta(days=1)


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


class TestCreate:
    def test_create_sets_identity_fields_and_records_event(self) -> None:
        organization_id = uuid4()
        recipient_user_id = uuid4()

        notification = _make_notification(
            organization_id=organization_id, recipient_user_id=recipient_user_id
        )

        assert notification.organization_id == organization_id
        assert notification.recipient_user_id == recipient_user_id
        events = notification.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], NotificationCreated)
        assert events[0].notification_id == notification.id
        assert events[0].recipient_user_id == recipient_user_id

    def test_without_scheduled_at_starts_pending(self) -> None:
        assert _make_notification().status is NotificationStatus.PENDING

    def test_with_scheduled_at_starts_scheduled(self) -> None:
        notification = _make_notification(scheduled_at=_FUTURE)
        assert notification.status is NotificationStatus.SCHEDULED

    def test_blank_title_is_rejected(self) -> None:
        with pytest.raises(NotificationTitleRequiredError):
            _make_notification(title="   ")

    def test_title_is_stripped(self) -> None:
        notification = _make_notification(title="  Reminder  ")
        assert notification.title == "Reminder"

    def test_blank_message_is_rejected(self) -> None:
        with pytest.raises(NotificationMessageRequiredError):
            _make_notification(message="   ")

    def test_message_is_stripped(self) -> None:
        notification = _make_notification(message="  Please confirm.  ")
        assert notification.message == "Please confirm."

    def test_reference_type_without_reference_id_is_rejected(self) -> None:
        with pytest.raises(InvalidNotificationReferenceError):
            _make_notification(reference_type="appointment", reference_id=None)

    def test_reference_id_without_reference_type_is_rejected(self) -> None:
        with pytest.raises(InvalidNotificationReferenceError):
            _make_notification(reference_type=None, reference_id=uuid4())

    def test_reference_type_and_reference_id_together_are_allowed(self) -> None:
        reference_id = uuid4()
        notification = _make_notification(reference_type="appointment", reference_id=reference_id)
        assert notification.reference_type == "appointment"
        assert notification.reference_id == reference_id

    def test_neither_reference_field_is_allowed(self) -> None:
        notification = _make_notification()
        assert notification.reference_type is None
        assert notification.reference_id is None

    def test_scheduled_at_after_expires_at_is_rejected(self) -> None:
        with pytest.raises(InvalidNotificationScheduleError):
            _make_notification(
                scheduled_at=datetime(2026, 6, 10, tzinfo=UTC),
                expires_at=datetime(2026, 6, 1, tzinfo=UTC),
            )

    def test_scheduled_at_equal_to_expires_at_is_allowed(self) -> None:
        same_instant = datetime(2026, 6, 1, tzinfo=UTC)
        notification = _make_notification(scheduled_at=same_instant, expires_at=same_instant)
        assert notification.scheduled_at == same_instant
        assert notification.expires_at == same_instant

    def test_only_expires_at_set_is_allowed(self) -> None:
        notification = _make_notification(expires_at=_FUTURE)
        assert notification.expires_at == _FUTURE

    def test_optional_fields_default_to_none(self) -> None:
        notification = _make_notification()
        assert notification.reference_type is None
        assert notification.reference_id is None
        assert notification.scheduled_at is None
        assert notification.sent_at is None
        assert notification.read_at is None
        assert notification.expires_at is None
        assert notification.metadata is None

    def test_metadata_is_preserved(self) -> None:
        notification = _make_notification(metadata={"channel_hint": "in_app"})
        assert notification.metadata == {"channel_hint": "in_app"}


class TestMarkSent:
    def test_mark_sent_from_pending_sets_status_and_timestamp(self) -> None:
        notification = _make_notification()
        notification.pull_events()

        notification.mark_sent()

        assert notification.status is NotificationStatus.SENT
        assert notification.sent_at is not None
        events = notification.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], NotificationStatusChanged)
        assert events[0].status == "sent"

    def test_mark_sent_from_scheduled_is_allowed(self) -> None:
        notification = _make_notification(scheduled_at=_FUTURE)
        notification.mark_sent()
        assert notification.status is NotificationStatus.SENT

    def test_mark_sent_twice_is_rejected(self) -> None:
        notification = _make_notification()
        notification.mark_sent()
        with pytest.raises(InvalidNotificationStatusTransitionError):
            notification.mark_sent()

    def test_mark_sent_past_expiry_raises_and_leaves_status_unchanged(self) -> None:
        notification = _make_notification(expires_at=_PAST)
        with pytest.raises(NotificationExpiredError):
            notification.mark_sent()
        assert notification.status is NotificationStatus.PENDING
        assert notification.sent_at is None

    def test_mark_sent_before_future_expiry_is_allowed(self) -> None:
        notification = _make_notification(expires_at=_FUTURE)
        notification.mark_sent()
        assert notification.status is NotificationStatus.SENT

    def test_mark_sent_on_an_already_expired_notification_raises_transition_error(self) -> None:
        """Once `status` is already `Expired` (e.g. via a prior
        `mark_expired()` call), `mark_sent()` must reject it as an
        invalid *transition* rather than re-reporting the expiry —
        `Expired` is terminal regardless of `expires_at`'s value."""
        notification = _make_notification(expires_at=_PAST)
        notification.mark_expired()
        with pytest.raises(InvalidNotificationStatusTransitionError):
            notification.mark_sent()


class TestMarkDelivered:
    def test_mark_delivered_from_sent_sets_status(self) -> None:
        notification = _make_notification()
        notification.mark_sent()
        notification.mark_delivered()
        assert notification.status is NotificationStatus.DELIVERED

    def test_mark_delivered_from_pending_is_rejected(self) -> None:
        notification = _make_notification()
        with pytest.raises(InvalidNotificationStatusTransitionError):
            notification.mark_delivered()


class TestMarkRead:
    def test_mark_read_from_delivered_sets_status_and_timestamp(self) -> None:
        notification = _make_notification()
        notification.mark_sent()
        notification.mark_delivered()
        notification.pull_events()

        notification.mark_read()

        assert notification.status is NotificationStatus.READ
        assert notification.read_at is not None
        events = notification.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], NotificationStatusChanged)
        assert events[0].status == "read"

    def test_mark_read_from_sent_is_rejected(self) -> None:
        notification = _make_notification()
        notification.mark_sent()
        with pytest.raises(InvalidNotificationStatusTransitionError):
            notification.mark_read()

    def test_read_cannot_become_unread(self) -> None:
        """ "Read notifications cannot become unread" — `Read` is terminal:
        no outgoing transition exists at all, including back to
        `Delivered`."""
        notification = _make_notification()
        notification.mark_sent()
        notification.mark_delivered()
        notification.mark_read()
        with pytest.raises(InvalidNotificationStatusTransitionError):
            notification.mark_delivered()


class TestCancel:
    def test_cancel_from_pending_sets_status(self) -> None:
        notification = _make_notification()
        notification.cancel()
        assert notification.status is NotificationStatus.CANCELLED

    def test_cancel_from_scheduled_is_allowed(self) -> None:
        notification = _make_notification(scheduled_at=_FUTURE)
        notification.cancel()
        assert notification.status is NotificationStatus.CANCELLED

    def test_cancelled_cannot_become_delivered(self) -> None:
        """ "Cancelled notifications cannot be delivered" — `Cancelled` is
        terminal."""
        notification = _make_notification()
        notification.cancel()
        with pytest.raises(InvalidNotificationStatusTransitionError):
            notification.mark_delivered()

    def test_cancel_once_sent_is_rejected(self) -> None:
        notification = _make_notification()
        notification.mark_sent()
        with pytest.raises(InvalidNotificationStatusTransitionError):
            notification.cancel()


class TestMarkExpired:
    def test_mark_expired_from_pending_sets_status(self) -> None:
        notification = _make_notification()
        notification.mark_expired()
        assert notification.status is NotificationStatus.EXPIRED

    def test_mark_expired_from_scheduled_is_allowed(self) -> None:
        notification = _make_notification(scheduled_at=_FUTURE)
        notification.mark_expired()
        assert notification.status is NotificationStatus.EXPIRED

    def test_expired_cannot_be_sent(self) -> None:
        """ "Expired notifications cannot be sent" — `Expired` is
        terminal."""
        notification = _make_notification()
        notification.mark_expired()
        with pytest.raises(InvalidNotificationStatusTransitionError):
            notification.mark_sent()

    def test_mark_expired_once_sent_is_rejected(self) -> None:
        notification = _make_notification()
        notification.mark_sent()
        with pytest.raises(InvalidNotificationStatusTransitionError):
            notification.mark_expired()
