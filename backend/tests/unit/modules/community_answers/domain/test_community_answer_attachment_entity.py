"""Tests for the `CommunityAnswerAttachment` aggregate root."""

from uuid import uuid4

from app.modules.community_answers.domain.entities import CommunityAnswerAttachment
from app.modules.community_answers.domain.events import CommunityAnswerAttachmentAdded
from app.modules.community_answers.domain.value_objects import AnswerId


class TestCommunityAnswerAttachmentCreate:
    def test_sets_required_fields(self) -> None:
        answer_id = AnswerId(uuid4())
        document_id = uuid4()
        attachment = CommunityAnswerAttachment.create(answer_id=answer_id, document_id=document_id)
        assert attachment.answer_id == answer_id
        assert attachment.document_id == document_id

    def test_assigns_a_unique_id(self) -> None:
        first = CommunityAnswerAttachment.create(answer_id=AnswerId(uuid4()), document_id=uuid4())
        second = CommunityAnswerAttachment.create(answer_id=AnswerId(uuid4()), document_id=uuid4())
        assert first.id != second.id

    def test_records_a_community_answer_attachment_added_event(self) -> None:
        answer_id = AnswerId(uuid4())
        document_id = uuid4()
        attachment = CommunityAnswerAttachment.create(answer_id=answer_id, document_id=document_id)
        events = attachment.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityAnswerAttachmentAdded)
        assert event.attachment_id == attachment.id
        assert event.answer_id == answer_id.value
        assert event.document_id == document_id

    def test_pull_events_drains_the_queue(self) -> None:
        attachment = CommunityAnswerAttachment.create(
            answer_id=AnswerId(uuid4()), document_id=uuid4()
        )
        attachment.pull_events()
        assert attachment.pull_events() == []
