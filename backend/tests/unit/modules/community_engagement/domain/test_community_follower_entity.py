"""Tests for the `CommunityFollower` aggregate root."""

from uuid import uuid4

from app.modules.community_engagement.domain.entities import CommunityFollower
from app.modules.community_engagement.domain.events import CommunityFollowed, CommunityUnfollowed


def _follower(**overrides: object) -> CommunityFollower:
    defaults: dict[str, object] = {
        "user_id": uuid4(),
        "organization_id": uuid4(),
        "community_id": uuid4(),
    }
    defaults.update(overrides)
    return CommunityFollower.create(**defaults)  # type: ignore[arg-type]


class TestCommunityFollowerCreate:
    def test_sets_required_fields(self) -> None:
        user_id = uuid4()
        organization_id = uuid4()
        community_id = uuid4()
        follower = CommunityFollower.create(
            user_id=user_id, organization_id=organization_id, community_id=community_id
        )
        assert follower.user_id == user_id
        assert follower.organization_id == organization_id
        assert follower.community_id == community_id

    def test_assigns_a_unique_id(self) -> None:
        first = _follower()
        second = _follower()
        assert first.id != second.id

    def test_records_a_community_followed_event(self) -> None:
        user_id = uuid4()
        community_id = uuid4()
        follower = _follower(user_id=user_id, community_id=community_id)
        events = follower.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityFollowed)
        assert event.community_follower_id == follower.id
        assert event.user_id == user_id
        assert event.community_id == community_id

    def test_pull_events_drains_the_queue(self) -> None:
        follower = _follower()
        follower.pull_events()
        assert follower.pull_events() == []


class TestCommunityFollowerMarkRemoved:
    def test_records_a_community_unfollowed_event(self) -> None:
        user_id = uuid4()
        community_id = uuid4()
        follower = _follower(user_id=user_id, community_id=community_id)
        follower.pull_events()
        follower.mark_removed()
        events = follower.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityUnfollowed)
        assert event.community_follower_id == follower.id
        assert event.user_id == user_id
        assert event.community_id == community_id
