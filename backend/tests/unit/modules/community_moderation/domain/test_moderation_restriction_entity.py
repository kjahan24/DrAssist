"""Unit tests for `ModerationRestriction`: creation, the `reason`
requirement, and `is_active()`'s time-window computation — the entity has
no mutation method beyond `issue()`, per its own module docstring."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.modules.community_moderation.domain.entities import ModerationRestriction
from app.modules.community_moderation.domain.enums import ModerationRestrictionType
from app.modules.community_moderation.domain.events import ModerationRestrictionIssued
from app.modules.community_moderation.domain.exceptions import ModerationReasonRequiredError


def _make_restriction(**overrides: object) -> ModerationRestriction:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "community_id": uuid4(),
        "user_id": uuid4(),
        "issued_by": uuid4(),
        "restriction_type": ModerationRestrictionType.WARNING,
        "reason": "Repeated spam links.",
    }
    defaults.update(overrides)
    return ModerationRestriction.issue(**defaults)  # type: ignore[arg-type]


class TestIssue:
    def test_stores_every_field(self) -> None:
        user_id, community_id, issued_by = uuid4(), uuid4(), uuid4()
        restriction = _make_restriction(
            user_id=user_id,
            community_id=community_id,
            issued_by=issued_by,
            restriction_type=ModerationRestrictionType.SUSPENSION,
        )
        assert restriction.user_id == user_id
        assert restriction.community_id == community_id
        assert restriction.issued_by == issued_by
        assert restriction.restriction_type is ModerationRestrictionType.SUSPENSION

    def test_defaults_ends_at_to_none(self) -> None:
        restriction = _make_restriction()
        assert restriction.ends_at is None

    def test_accepts_an_explicit_ends_at(self) -> None:
        ends_at = datetime.now(UTC) + timedelta(days=7)
        restriction = _make_restriction(ends_at=ends_at)
        assert restriction.ends_at == ends_at

    def test_records_a_restriction_issued_event(self) -> None:
        restriction = _make_restriction()
        events = restriction.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ModerationRestrictionIssued)
        assert events[0].restriction_id == restriction.id

    def test_strips_surrounding_whitespace_from_reason(self) -> None:
        restriction = _make_restriction(reason="  Repeated spam.  ")
        assert restriction.reason == "Repeated spam."

    def test_blank_reason_raises(self) -> None:
        with pytest.raises(ModerationReasonRequiredError):
            _make_restriction(reason="   ")

    def test_accepts_an_optional_report_id(self) -> None:
        report_id = uuid4()
        restriction = _make_restriction(report_id=report_id)
        assert restriction.report_id == report_id


class TestIsActive:
    def test_permanent_restriction_is_always_active_once_started(self) -> None:
        restriction = _make_restriction(restriction_type=ModerationRestrictionType.PERMANENT_BAN)
        assert restriction.is_active() is True

    def test_permanent_restriction_is_active_far_in_the_future(self) -> None:
        restriction = _make_restriction(restriction_type=ModerationRestrictionType.PERMANENT_BAN)
        far_future = datetime.now(UTC) + timedelta(days=3650)
        assert restriction.is_active(now=far_future) is True

    def test_temporary_restriction_is_active_before_ends_at(self) -> None:
        starts_at = datetime.now(UTC) - timedelta(days=1)
        ends_at = datetime.now(UTC) + timedelta(days=6)
        restriction = _make_restriction(starts_at=starts_at, ends_at=ends_at)
        assert restriction.is_active(now=datetime.now(UTC)) is True

    def test_temporary_restriction_is_inactive_after_ends_at(self) -> None:
        starts_at = datetime.now(UTC) - timedelta(days=8)
        ends_at = datetime.now(UTC) - timedelta(days=1)
        restriction = _make_restriction(starts_at=starts_at, ends_at=ends_at)
        assert restriction.is_active(now=datetime.now(UTC)) is False

    def test_restriction_is_inactive_before_its_starts_at(self) -> None:
        starts_at = datetime.now(UTC) + timedelta(days=1)
        restriction = _make_restriction(starts_at=starts_at)
        assert restriction.is_active(now=datetime.now(UTC)) is False

    def test_defaults_now_to_the_current_time(self) -> None:
        starts_at = datetime.now(UTC) - timedelta(minutes=1)
        restriction = _make_restriction(starts_at=starts_at, ends_at=None)
        assert restriction.is_active() is True
