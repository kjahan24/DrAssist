"""Tests for the `CommunityPostTopic` aggregate root."""

from uuid import uuid4

from app.modules.community_posts.domain.entities import CommunityPostTopic
from app.modules.community_posts.domain.events import CommunityPostTopicAssigned
from app.modules.community_posts.domain.value_objects import PostId


def _post_id() -> PostId:
    return PostId(uuid4())


class TestCommunityPostTopicCreate:
    def test_sets_required_fields(self) -> None:
        post_id = _post_id()
        topic_id = uuid4()
        assignment = CommunityPostTopic.create(post_id=post_id, topic_id=topic_id)
        assert assignment.post_id == post_id
        assert assignment.topic_id == topic_id

    def test_assigns_a_unique_id(self) -> None:
        post_id = _post_id()
        first = CommunityPostTopic.create(post_id=post_id, topic_id=uuid4())
        second = CommunityPostTopic.create(post_id=post_id, topic_id=uuid4())
        assert first.id != second.id

    def test_records_a_community_post_topic_assigned_event(self) -> None:
        post_id = _post_id()
        topic_id = uuid4()
        assignment = CommunityPostTopic.create(post_id=post_id, topic_id=topic_id)
        events = assignment.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityPostTopicAssigned)
        assert event.post_topic_id == assignment.id
        assert event.post_id == post_id.value
        assert event.topic_id == topic_id

    def test_pull_events_drains_the_queue(self) -> None:
        assignment = CommunityPostTopic.create(post_id=_post_id(), topic_id=uuid4())
        assignment.pull_events()
        assert assignment.pull_events() == []
