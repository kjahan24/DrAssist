"""Tests for the `CommunityQuestionFollower` aggregate root."""

from uuid import uuid4

from app.modules.community_questions.domain.entities import CommunityQuestionFollower
from app.modules.community_questions.domain.events import CommunityQuestionFollowed
from app.modules.community_questions.domain.value_objects import QuestionId


def _question_id() -> QuestionId:
    return QuestionId(uuid4())


class TestCommunityQuestionFollowerCreate:
    def test_sets_required_fields(self) -> None:
        question_id = _question_id()
        user_id = uuid4()
        follower = CommunityQuestionFollower.create(question_id=question_id, user_id=user_id)
        assert follower.question_id == question_id
        assert follower.user_id == user_id

    def test_assigns_a_unique_id(self) -> None:
        question_id = _question_id()
        first = CommunityQuestionFollower.create(question_id=question_id, user_id=uuid4())
        second = CommunityQuestionFollower.create(question_id=question_id, user_id=uuid4())
        assert first.id != second.id

    def test_records_a_community_question_followed_event(self) -> None:
        question_id = _question_id()
        user_id = uuid4()
        follower = CommunityQuestionFollower.create(question_id=question_id, user_id=user_id)
        events = follower.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityQuestionFollowed)
        assert event.follower_id == follower.id
        assert event.question_id == question_id.value
        assert event.user_id == user_id

    def test_pull_events_drains_the_queue(self) -> None:
        follower = CommunityQuestionFollower.create(question_id=_question_id(), user_id=uuid4())
        follower.pull_events()
        assert follower.pull_events() == []
