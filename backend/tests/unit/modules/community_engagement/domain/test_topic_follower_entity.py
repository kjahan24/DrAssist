"""Tests for the `TopicFollower` aggregate root."""

from uuid import uuid4

from app.modules.community_engagement.domain.entities import TopicFollower
from app.modules.community_engagement.domain.events import TopicFollowed, TopicUnfollowed


def _follower(**overrides: object) -> TopicFollower:
    defaults: dict[str, object] = {
        "user_id": uuid4(),
        "organization_id": uuid4(),
        "topic_id": uuid4(),
    }
    defaults.update(overrides)
    return TopicFollower.create(**defaults)  # type: ignore[arg-type]


class TestTopicFollowerCreate:
    def test_sets_required_fields(self) -> None:
        user_id = uuid4()
        organization_id = uuid4()
        topic_id = uuid4()
        follower = TopicFollower.create(
            user_id=user_id, organization_id=organization_id, topic_id=topic_id
        )
        assert follower.user_id == user_id
        assert follower.organization_id == organization_id
        assert follower.topic_id == topic_id

    def test_assigns_a_unique_id(self) -> None:
        first = _follower()
        second = _follower()
        assert first.id != second.id

    def test_records_a_topic_followed_event(self) -> None:
        user_id = uuid4()
        topic_id = uuid4()
        follower = _follower(user_id=user_id, topic_id=topic_id)
        events = follower.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, TopicFollowed)
        assert event.topic_follower_id == follower.id
        assert event.user_id == user_id
        assert event.topic_id == topic_id

    def test_pull_events_drains_the_queue(self) -> None:
        follower = _follower()
        follower.pull_events()
        assert follower.pull_events() == []


class TestTopicFollowerMarkRemoved:
    def test_records_a_topic_unfollowed_event(self) -> None:
        user_id = uuid4()
        topic_id = uuid4()
        follower = _follower(user_id=user_id, topic_id=topic_id)
        follower.pull_events()
        follower.mark_removed()
        events = follower.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, TopicUnfollowed)
        assert event.topic_follower_id == follower.id
        assert event.user_id == user_id
        assert event.topic_id == topic_id
