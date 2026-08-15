"""Tests for the `CommunityQuestionAttachment` aggregate root."""

from uuid import uuid4

from app.modules.community_questions.domain.entities import CommunityQuestionAttachment
from app.modules.community_questions.domain.events import CommunityQuestionAttachmentAdded
from app.modules.community_questions.domain.value_objects import QuestionId


def _question_id() -> QuestionId:
    return QuestionId(uuid4())


class TestCommunityQuestionAttachmentCreate:
    def test_sets_required_fields(self) -> None:
        question_id = _question_id()
        document_id = uuid4()
        attachment = CommunityQuestionAttachment.create(
            question_id=question_id, document_id=document_id
        )
        assert attachment.question_id == question_id
        assert attachment.document_id == document_id

    def test_assigns_a_unique_id(self) -> None:
        question_id = _question_id()
        first = CommunityQuestionAttachment.create(question_id=question_id, document_id=uuid4())
        second = CommunityQuestionAttachment.create(question_id=question_id, document_id=uuid4())
        assert first.id != second.id

    def test_records_a_community_question_attachment_added_event(self) -> None:
        question_id = _question_id()
        document_id = uuid4()
        attachment = CommunityQuestionAttachment.create(
            question_id=question_id, document_id=document_id
        )
        events = attachment.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityQuestionAttachmentAdded)
        assert event.attachment_id == attachment.id
        assert event.question_id == question_id.value
        assert event.document_id == document_id

    def test_pull_events_drains_the_queue(self) -> None:
        attachment = CommunityQuestionAttachment.create(
            question_id=_question_id(), document_id=uuid4()
        )
        attachment.pull_events()
        assert attachment.pull_events() == []
