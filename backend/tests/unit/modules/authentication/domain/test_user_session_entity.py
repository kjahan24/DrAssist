"""Unit tests for the `UserSession` aggregate's invariants."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.modules.authentication.domain.entities import UserSession
from app.modules.authentication.domain.events import SessionCreated, SessionRevoked


class TestStart:
    def test_start_records_session_created_event(self) -> None:
        now = datetime.now(UTC)
        user_id = uuid4()
        session = UserSession.start(
            organization_id=uuid4(),
            user_id=user_id,
            expires_at=now + timedelta(days=30),
            now=now,
        )
        assert session.issued_at == now
        assert session.user_id == user_id
        events = session.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], SessionCreated)


class TestActiveState:
    def test_is_active_true_when_not_revoked_and_not_expired(self) -> None:
        now = datetime.now(UTC)
        session = UserSession.start(
            organization_id=uuid4(), user_id=uuid4(), expires_at=now + timedelta(days=1), now=now
        )
        assert session.is_active(now=now) is True

    def test_is_active_false_once_expired(self) -> None:
        now = datetime.now(UTC)
        session = UserSession.start(
            organization_id=uuid4(),
            user_id=uuid4(),
            expires_at=now - timedelta(seconds=1),
            now=now - timedelta(days=1),
        )
        assert session.is_active(now=now) is False

    def test_is_active_false_once_revoked(self) -> None:
        now = datetime.now(UTC)
        session = UserSession.start(
            organization_id=uuid4(), user_id=uuid4(), expires_at=now + timedelta(days=1), now=now
        )
        session.revoke(reason="logout", now=now)
        assert session.is_active(now=now) is False


class TestRevoke:
    def test_revoke_sets_reason_and_records_event(self) -> None:
        now = datetime.now(UTC)
        session = UserSession.start(
            organization_id=uuid4(), user_id=uuid4(), expires_at=now + timedelta(days=1), now=now
        )
        session.pull_events()

        session.revoke(reason="admin_revoked", now=now)

        assert session.revoked_reason == "admin_revoked"
        events = session.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], SessionRevoked)
        assert events[0].reason == "admin_revoked"

    def test_revoking_twice_is_idempotent(self) -> None:
        now = datetime.now(UTC)
        session = UserSession.start(
            organization_id=uuid4(), user_id=uuid4(), expires_at=now + timedelta(days=1), now=now
        )
        session.revoke(reason="logout", now=now)
        session.pull_events()

        session.revoke(reason="admin_revoked", now=now + timedelta(minutes=1))

        assert session.revoked_reason == "logout"  # first reason wins
        assert session.pull_events() == []


class TestMarkUsed:
    def test_mark_used_updates_last_used_at(self) -> None:
        now = datetime.now(UTC)
        session = UserSession.start(
            organization_id=uuid4(), user_id=uuid4(), expires_at=now + timedelta(days=1), now=now
        )
        later = now + timedelta(minutes=5)
        session.mark_used(now=later)
        assert session.last_used_at == later
