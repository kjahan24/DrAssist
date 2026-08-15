"""Tests for the `CommunityQuestionTag` aggregate root."""

from uuid import uuid4

import pytest

from app.modules.community_questions.domain.entities import CommunityQuestionTag
from app.modules.community_questions.domain.events import CommunityQuestionTagAssigned
from app.modules.community_questions.domain.exceptions import (
    QuestionTagRequiredError,
    QuestionTagTooLongError,
)
from app.modules.community_questions.domain.value_objects import QuestionId


def _question_id() -> QuestionId:
    return QuestionId(uuid4())


class TestCommunityQuestionTagCreate:
    def test_sets_required_fields(self) -> None:
        question_id = _question_id()
        assignment = CommunityQuestionTag.create(question_id=question_id, tag="diabetes")
        assert assignment.question_id == question_id
        assert assignment.tag == "diabetes"

    def test_normalizes_to_lowercase(self) -> None:
        assignment = CommunityQuestionTag.create(question_id=_question_id(), tag="Diabetes")
        assert assignment.tag == "diabetes"

    def test_strips_surrounding_whitespace(self) -> None:
        assignment = CommunityQuestionTag.create(question_id=_question_id(), tag="  diabetes  ")
        assert assignment.tag == "diabetes"

    @pytest.mark.parametrize("raw", ["", "   "])
    def test_blank_tag_raises(self, raw: str) -> None:
        with pytest.raises(QuestionTagRequiredError):
            CommunityQuestionTag.create(question_id=_question_id(), tag=raw)

    def test_tag_over_max_length_raises(self) -> None:
        with pytest.raises(QuestionTagTooLongError):
            CommunityQuestionTag.create(question_id=_question_id(), tag="a" * 51)

    def test_tag_at_max_length_boundary_is_valid(self) -> None:
        tag = "a" * 50
        assignment = CommunityQuestionTag.create(question_id=_question_id(), tag=tag)
        assert assignment.tag == tag

    def test_assigns_a_unique_id(self) -> None:
        question_id = _question_id()
        first = CommunityQuestionTag.create(question_id=question_id, tag="diabetes")
        second = CommunityQuestionTag.create(question_id=question_id, tag="oncology")
        assert first.id != second.id

    def test_records_a_community_question_tag_assigned_event(self) -> None:
        question_id = _question_id()
        assignment = CommunityQuestionTag.create(question_id=question_id, tag="diabetes")
        events = assignment.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityQuestionTagAssigned)
        assert event.question_tag_id == assignment.id
        assert event.question_id == question_id.value
        assert event.tag == "diabetes"

    def test_pull_events_drains_the_queue(self) -> None:
        assignment = CommunityQuestionTag.create(question_id=_question_id(), tag="diabetes")
        assignment.pull_events()
        assert assignment.pull_events() == []
