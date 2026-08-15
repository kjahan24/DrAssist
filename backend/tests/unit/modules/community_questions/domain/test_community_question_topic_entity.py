"""Tests for the `CommunityQuestionTopic` aggregate root."""

from uuid import uuid4

from app.modules.community_questions.domain.entities import CommunityQuestionTopic
from app.modules.community_questions.domain.events import CommunityQuestionTopicAssigned
from app.modules.community_questions.domain.value_objects import QuestionId


def _question_id() -> QuestionId:
    return QuestionId(uuid4())


class TestCommunityQuestionTopicCreate:
    def test_sets_required_fields(self) -> None:
        question_id = _question_id()
        topic_id = uuid4()
        assignment = CommunityQuestionTopic.create(question_id=question_id, topic_id=topic_id)
        assert assignment.question_id == question_id
        assert assignment.topic_id == topic_id

    def test_assigns_a_unique_id(self) -> None:
        question_id = _question_id()
        first = CommunityQuestionTopic.create(question_id=question_id, topic_id=uuid4())
        second = CommunityQuestionTopic.create(question_id=question_id, topic_id=uuid4())
        assert first.id != second.id

    def test_records_a_community_question_topic_assigned_event(self) -> None:
        question_id = _question_id()
        topic_id = uuid4()
        assignment = CommunityQuestionTopic.create(question_id=question_id, topic_id=topic_id)
        events = assignment.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityQuestionTopicAssigned)
        assert event.question_topic_id == assignment.id
        assert event.question_id == question_id.value
        assert event.topic_id == topic_id

    def test_pull_events_drains_the_queue(self) -> None:
        assignment = CommunityQuestionTopic.create(question_id=_question_id(), topic_id=uuid4())
        assignment.pull_events()
        assert assignment.pull_events() == []
