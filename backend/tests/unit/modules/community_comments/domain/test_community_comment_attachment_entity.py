"""Tests for the `CommunityCommentAttachment` aggregate root."""

from uuid import uuid4

from app.modules.community_comments.domain.entities import CommunityCommentAttachment
from app.modules.community_comments.domain.events import CommunityCommentAttachmentAdded
from app.modules.community_comments.domain.value_objects import CommentId


class TestCommunityCommentAttachmentCreate:
    def test_sets_required_fields(self) -> None:
        comment_id = CommentId(uuid4())
        document_id = uuid4()
        attachment = CommunityCommentAttachment.create(
            comment_id=comment_id, document_id=document_id
        )
        assert attachment.comment_id == comment_id
        assert attachment.document_id == document_id

    def test_assigns_a_unique_id(self) -> None:
        first = CommunityCommentAttachment.create(
            comment_id=CommentId(uuid4()), document_id=uuid4()
        )
        second = CommunityCommentAttachment.create(
            comment_id=CommentId(uuid4()), document_id=uuid4()
        )
        assert first.id != second.id

    def test_records_a_community_comment_attachment_added_event(self) -> None:
        comment_id = CommentId(uuid4())
        document_id = uuid4()
        attachment = CommunityCommentAttachment.create(
            comment_id=comment_id, document_id=document_id
        )
        events = attachment.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityCommentAttachmentAdded)
        assert event.attachment_id == attachment.id
        assert event.comment_id == comment_id.value
        assert event.document_id == document_id

    def test_pull_events_drains_the_queue(self) -> None:
        attachment = CommunityCommentAttachment.create(
            comment_id=CommentId(uuid4()), document_id=uuid4()
        )
        attachment.pull_events()
        assert attachment.pull_events() == []
