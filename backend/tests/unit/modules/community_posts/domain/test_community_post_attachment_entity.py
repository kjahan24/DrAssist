"""Tests for the `CommunityPostAttachment` aggregate root."""

from uuid import uuid4

from app.modules.community_posts.domain.entities import CommunityPostAttachment
from app.modules.community_posts.domain.events import CommunityPostAttachmentAdded
from app.modules.community_posts.domain.value_objects import PostId


def _post_id() -> PostId:
    return PostId(uuid4())


class TestCommunityPostAttachmentCreate:
    def test_sets_required_fields(self) -> None:
        post_id = _post_id()
        document_id = uuid4()
        attachment = CommunityPostAttachment.create(post_id=post_id, document_id=document_id)
        assert attachment.post_id == post_id
        assert attachment.document_id == document_id

    def test_assigns_a_unique_id(self) -> None:
        post_id = _post_id()
        first = CommunityPostAttachment.create(post_id=post_id, document_id=uuid4())
        second = CommunityPostAttachment.create(post_id=post_id, document_id=uuid4())
        assert first.id != second.id

    def test_records_a_community_post_attachment_added_event(self) -> None:
        post_id = _post_id()
        document_id = uuid4()
        attachment = CommunityPostAttachment.create(post_id=post_id, document_id=document_id)
        events = attachment.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityPostAttachmentAdded)
        assert event.attachment_id == attachment.id
        assert event.post_id == post_id.value
        assert event.document_id == document_id

    def test_pull_events_drains_the_queue(self) -> None:
        attachment = CommunityPostAttachment.create(post_id=_post_id(), document_id=uuid4())
        attachment.pull_events()
        assert attachment.pull_events() == []
