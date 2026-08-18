"""Tests for the `CommunityCommentRevision` aggregate root — see its own
docstring: append-only and immutable, no mutating methods beyond
`.create()`."""

from uuid import uuid4

from app.modules.community_comments.domain.entities import CommunityCommentRevision
from app.modules.community_comments.domain.events import CommunityCommentRevisionCreated
from app.modules.community_comments.domain.value_objects import CommentId


class TestCommunityCommentRevisionCreate:
    def test_sets_required_fields(self) -> None:
        comment_id = CommentId(uuid4())
        author_id = uuid4()
        revision = CommunityCommentRevision.create(
            comment_id=comment_id,
            revision_number=1,
            previous_body="The previous body text.",
            author_id=author_id,
        )
        assert revision.comment_id == comment_id
        assert revision.revision_number == 1
        assert revision.previous_body == "The previous body text."
        assert revision.author_id == author_id

    def test_assigns_a_unique_id(self) -> None:
        first = CommunityCommentRevision.create(
            comment_id=CommentId(uuid4()),
            revision_number=1,
            previous_body="body",
            author_id=uuid4(),
        )
        second = CommunityCommentRevision.create(
            comment_id=CommentId(uuid4()),
            revision_number=1,
            previous_body="body",
            author_id=uuid4(),
        )
        assert first.id != second.id

    def test_records_a_community_comment_revision_created_event(self) -> None:
        comment_id = CommentId(uuid4())
        revision = CommunityCommentRevision.create(
            comment_id=comment_id, revision_number=3, previous_body="body", author_id=uuid4()
        )
        events = revision.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityCommentRevisionCreated)
        assert event.revision_id == revision.id
        assert event.comment_id == comment_id.value
        assert event.revision_number == 3

    def test_pull_events_drains_the_queue(self) -> None:
        revision = CommunityCommentRevision.create(
            comment_id=CommentId(uuid4()),
            revision_number=1,
            previous_body="body",
            author_id=uuid4(),
        )
        revision.pull_events()
        assert revision.pull_events() == []

    def test_has_no_public_mutating_methods_beyond_create(self) -> None:
        own_methods = {
            name
            for name in vars(CommunityCommentRevision)
            if not name.startswith("_") and callable(getattr(CommunityCommentRevision, name))
        }
        assert own_methods == {"create"}
