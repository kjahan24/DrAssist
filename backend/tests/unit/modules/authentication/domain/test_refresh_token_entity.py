"""Unit tests for `RefreshToken` — rotation and reuse detection are the
security-critical behaviors here."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.modules.authentication.domain.entities import RefreshToken
from app.modules.authentication.domain.events import RefreshTokenIssued, RefreshTokenRotated
from app.modules.authentication.domain.exceptions import (
    RefreshTokenAlreadyUsedError,
    RefreshTokenExpiredError,
)


def _issue(now: datetime, expires_in: timedelta = timedelta(days=7)) -> RefreshToken:
    token = RefreshToken.issue(
        organization_id=uuid4(),
        user_session_id=uuid4(),
        token_hash="hash-value",
        expires_at=now + expires_in,
        now=now,
    )
    token.pull_events()
    return token


class TestIssue:
    def test_issue_records_refresh_token_issued_event(self) -> None:
        now = datetime.now(UTC)
        token = RefreshToken.issue(
            organization_id=uuid4(),
            user_session_id=uuid4(),
            token_hash="abc",
            expires_at=now + timedelta(days=7),
            now=now,
        )
        events = token.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], RefreshTokenIssued)


class TestIsActive:
    def test_active_when_unused_unrevoked_and_unexpired(self) -> None:
        now = datetime.now(UTC)
        token = _issue(now)
        assert token.is_active(now=now) is True

    def test_inactive_once_expired(self) -> None:
        now = datetime.now(UTC)
        token = _issue(now, expires_in=timedelta(seconds=1))
        assert token.is_active(now=now + timedelta(seconds=2)) is False


class TestRotate:
    def test_rotate_marks_used_and_links_replacement(self) -> None:
        now = datetime.now(UTC)
        token = _issue(now)
        new_id = uuid4()

        token.rotate(new_token_id=new_id, now=now)

        assert token.used_at == now
        assert token.replaced_by_token_id == new_id
        assert token.is_active(now=now) is False
        events = token.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], RefreshTokenRotated)
        assert events[0].new_token_id == new_id

    def test_rotating_an_already_used_token_raises_reuse_error(self) -> None:
        now = datetime.now(UTC)
        token = _issue(now)
        token.rotate(new_token_id=uuid4(), now=now)

        with pytest.raises(RefreshTokenAlreadyUsedError):
            token.rotate(new_token_id=uuid4(), now=now)

    def test_rotating_a_revoked_token_raises_reuse_error(self) -> None:
        now = datetime.now(UTC)
        token = _issue(now)
        token.revoke(reason="logout", now=now)

        with pytest.raises(RefreshTokenAlreadyUsedError):
            token.rotate(new_token_id=uuid4(), now=now)

    def test_rotating_an_expired_token_raises_expired_error(self) -> None:
        now = datetime.now(UTC)
        token = _issue(now, expires_in=timedelta(seconds=1))

        with pytest.raises(RefreshTokenExpiredError):
            token.rotate(new_token_id=uuid4(), now=now + timedelta(seconds=2))


class TestRevoke:
    def test_revoke_is_idempotent(self) -> None:
        now = datetime.now(UTC)
        token = _issue(now)
        token.revoke(reason="first", now=now)
        token.pull_events()

        token.revoke(reason="second", now=now)

        assert token.revoked_reason == "first"
        assert token.pull_events() == []
