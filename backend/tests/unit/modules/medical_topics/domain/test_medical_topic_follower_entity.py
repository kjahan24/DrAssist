"""Tests for the `MedicalTopicFollower` aggregate root."""

from uuid import uuid4

from app.modules.medical_topics.domain.entities import MedicalTopicFollower
from app.modules.medical_topics.domain.events import TopicFollowed
from app.modules.medical_topics.domain.value_objects import TopicId


def _topic_id() -> TopicId:
    return TopicId(uuid4())


class TestMedicalTopicFollowerCreate:
    def test_sets_required_fields(self) -> None:
        topic_id = _topic_id()
        user_id = uuid4()
        follower = MedicalTopicFollower.create(topic_id=topic_id, user_id=user_id)
        assert follower.topic_id == topic_id
        assert follower.user_id == user_id

    def test_assigns_a_unique_id(self) -> None:
        topic_id = _topic_id()
        first = MedicalTopicFollower.create(topic_id=topic_id, user_id=uuid4())
        second = MedicalTopicFollower.create(topic_id=topic_id, user_id=uuid4())
        assert first.id != second.id

    def test_records_a_topic_followed_event(self) -> None:
        topic_id = _topic_id()
        user_id = uuid4()
        follower = MedicalTopicFollower.create(topic_id=topic_id, user_id=user_id)
        events = follower.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, TopicFollowed)
        assert event.topic_id == topic_id.value
        assert event.user_id == user_id

    def test_pull_events_drains_the_queue(self) -> None:
        follower = MedicalTopicFollower.create(topic_id=_topic_id(), user_id=uuid4())
        follower.pull_events()
        assert follower.pull_events() == []
