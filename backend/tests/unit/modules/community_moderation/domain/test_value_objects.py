"""Unit tests for the `UserModerationStatus` value object."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.modules.community_moderation.domain.enums import ModerationRestrictionType
from app.modules.community_moderation.domain.value_objects import UserModerationStatus


class TestUserModerationStatus:
    def test_is_restricted_true_when_a_restriction_type_is_present(self) -> None:
        status = UserModerationStatus(
            user_id=uuid4(),
            community_id=uuid4(),
            current_restriction_type=ModerationRestrictionType.SUSPENSION,
            restricted_until=datetime.now(UTC) + timedelta(days=7),
            active_restriction_count=1,
        )
        assert status.is_restricted is True

    def test_is_restricted_false_when_no_restriction_type(self) -> None:
        status = UserModerationStatus(
            user_id=uuid4(),
            community_id=uuid4(),
            current_restriction_type=None,
            restricted_until=None,
            active_restriction_count=0,
        )
        assert status.is_restricted is False

    def test_is_frozen(self) -> None:
        status = UserModerationStatus(
            user_id=uuid4(),
            community_id=None,
            current_restriction_type=None,
            restricted_until=None,
            active_restriction_count=0,
        )
        with pytest.raises(AttributeError):
            status.active_restriction_count = 5  # type: ignore[misc]

    def test_community_id_may_be_none_for_a_platform_wide_view(self) -> None:
        status = UserModerationStatus(
            user_id=uuid4(),
            community_id=None,
            current_restriction_type=ModerationRestrictionType.WARNING,
            restricted_until=None,
            active_restriction_count=2,
        )
        assert status.community_id is None
        assert status.active_restriction_count == 2
