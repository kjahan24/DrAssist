"""Tests for the `CommunityComment` aggregate root."""

from uuid import uuid4

from app.modules.community_comments.domain.entities import MAX_COMMENT_DEPTH, CommunityComment
from app.modules.community_comments.domain.enums import CommentStatus, CommentTargetType
from app.modules.community_comments.domain.events import (
    CommunityCommentArchived,
    CommunityCommentCreated,
    CommunityCommentDeleted,
    CommunityCommentPublished,
    CommunityCommentRestored,
    CommunityCommentUpdated,
)
from app.modules.community_comments.domain.exceptions import (
    CommentAlreadyArchivedError,
    CommentAlreadyDeletedError,
    CommentAlreadyPublishedError,
    CommentBodyRequiredError,
    CommentCannotBeRestoredError,
    MaxCommentDepthExceededError,
)
from app.modules.community_comments.domain.value_objects import CommentBody


def _comment(**overrides: object) -> CommunityComment:
    defaults: dict[str, object] = {
        "target_type": CommentTargetType.POST,
        "target_id": uuid4(),
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "topic_id": None,
        "author_id": uuid4(),
        "body": CommentBody("This is the body of the comment."),
    }
    defaults.update(overrides)
    return CommunityComment.create(**defaults)  # type: ignore[arg-type]


class TestCommunityCommentCreate:
    def test_sets_required_fields(self) -> None:
        target_type = CommentTargetType.QUESTION
        target_id = uuid4()
        community_id = uuid4()
        organization_id = uuid4()
        topic_id = uuid4()
        author_id = uuid4()
        comment = CommunityComment.create(
            target_type=target_type,
            target_id=target_id,
            community_id=community_id,
            organization_id=organization_id,
            topic_id=topic_id,
            author_id=author_id,
            body=CommentBody("Some body text."),
        )
        assert comment.target_type is target_type
        assert comment.target_id == target_id
        assert comment.community_id == community_id
        assert comment.organization_id == organization_id
        assert comment.topic_id == topic_id
        assert comment.author_id == author_id

    def test_defaults_to_draft_status(self) -> None:
        comment = _comment()
        assert comment.status is CommentStatus.DRAFT

    def test_defaults_to_not_anonymous(self) -> None:
        comment = _comment()
        assert comment.is_anonymous is False

    def test_accepts_is_anonymous(self) -> None:
        comment = _comment(is_anonymous=True)
        assert comment.is_anonymous is True

    def test_defaults_revision_number_to_one(self) -> None:
        comment = _comment()
        assert comment.revision_number == 1

    def test_defaults_published_at_to_none(self) -> None:
        comment = _comment()
        assert comment.published_at is None

    def test_updated_by_defaults_to_author_id(self) -> None:
        author_id = uuid4()
        comment = _comment(author_id=author_id)
        assert comment.updated_by == author_id

    def test_top_level_comment_has_no_parent(self) -> None:
        comment = _comment()
        assert comment.parent_comment_id is None

    def test_top_level_comment_is_its_own_root(self) -> None:
        comment = _comment()
        assert comment.root_comment_id == comment.id

    def test_top_level_comment_has_depth_zero(self) -> None:
        comment = _comment()
        assert comment.depth == 0

    def test_topic_id_may_be_none(self) -> None:
        comment = _comment(topic_id=None)
        assert comment.topic_id is None

    def test_assigns_a_unique_id(self) -> None:
        first = _comment()
        second = _comment()
        assert first.id != second.id

    def test_records_a_community_comment_created_event(self) -> None:
        author_id = uuid4()
        target_id = uuid4()
        comment = _comment(
            author_id=author_id, target_id=target_id, target_type=CommentTargetType.ANSWER
        )
        events = comment.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityCommentCreated)
        assert event.comment_id == comment.id
        assert event.target_type is CommentTargetType.ANSWER
        assert event.target_id == target_id
        assert event.author_id == author_id
        assert event.parent_comment_id is None

    def test_pull_events_drains_the_queue(self) -> None:
        comment = _comment()
        comment.pull_events()
        assert comment.pull_events() == []

    def test_blank_body_raises(self) -> None:
        try:
            CommentBody("   ")
            raised = False
        except CommentBodyRequiredError:
            raised = True
        assert raised is True


class TestCommunityCommentCreateReply:
    def test_inherits_target_from_parent(self) -> None:
        target_id = uuid4()
        parent = _comment(target_type=CommentTargetType.QUESTION, target_id=target_id)
        reply = CommunityComment.create_reply(
            parent=parent, author_id=uuid4(), body=CommentBody("A reply.")
        )
        assert reply.target_type is CommentTargetType.QUESTION
        assert reply.target_id == target_id

    def test_inherits_community_organization_and_topic_from_parent(self) -> None:
        community_id, organization_id, topic_id = uuid4(), uuid4(), uuid4()
        parent = _comment(
            community_id=community_id, organization_id=organization_id, topic_id=topic_id
        )
        reply = CommunityComment.create_reply(
            parent=parent, author_id=uuid4(), body=CommentBody("A reply.")
        )
        assert reply.community_id == community_id
        assert reply.organization_id == organization_id
        assert reply.topic_id == topic_id

    def test_sets_parent_comment_id_to_the_parents_own_id(self) -> None:
        parent = _comment()
        reply = CommunityComment.create_reply(
            parent=parent, author_id=uuid4(), body=CommentBody("A reply.")
        )
        assert reply.parent_comment_id == parent.id

    def test_replying_to_a_top_level_comment_has_depth_one(self) -> None:
        parent = _comment()
        reply = CommunityComment.create_reply(
            parent=parent, author_id=uuid4(), body=CommentBody("A reply.")
        )
        assert reply.depth == 1

    def test_reply_inherits_the_parents_own_root_comment_id(self) -> None:
        parent = _comment()
        reply = CommunityComment.create_reply(
            parent=parent, author_id=uuid4(), body=CommentBody("A reply.")
        )
        assert reply.root_comment_id == parent.root_comment_id

    def test_a_reply_to_a_reply_shares_the_same_root(self) -> None:
        root = _comment()
        first_reply = CommunityComment.create_reply(
            parent=root, author_id=uuid4(), body=CommentBody("First reply.")
        )
        second_reply = CommunityComment.create_reply(
            parent=first_reply, author_id=uuid4(), body=CommentBody("Reply to a reply.")
        )
        assert second_reply.root_comment_id == root.id
        assert second_reply.depth == 2

    def test_uses_the_given_author_id_not_the_parents(self) -> None:
        parent = _comment(author_id=uuid4())
        reply_author_id = uuid4()
        reply = CommunityComment.create_reply(
            parent=parent, author_id=reply_author_id, body=CommentBody("A reply.")
        )
        assert reply.author_id == reply_author_id

    def test_accepts_is_anonymous(self) -> None:
        parent = _comment()
        reply = CommunityComment.create_reply(
            parent=parent, author_id=uuid4(), body=CommentBody("A reply."), is_anonymous=True
        )
        assert reply.is_anonymous is True

    def test_assigns_a_unique_id_distinct_from_the_parent(self) -> None:
        parent = _comment()
        reply = CommunityComment.create_reply(
            parent=parent, author_id=uuid4(), body=CommentBody("A reply.")
        )
        assert reply.id != parent.id

    def test_records_a_community_comment_created_event_with_the_parent_id(self) -> None:
        parent = _comment()
        reply_author_id = uuid4()
        reply = CommunityComment.create_reply(
            parent=parent, author_id=reply_author_id, body=CommentBody("A reply.")
        )
        events = reply.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityCommentCreated)
        assert event.comment_id == reply.id
        assert event.parent_comment_id == parent.id
        assert event.author_id == reply_author_id

    def test_exceeding_max_depth_raises(self) -> None:
        current = _comment()
        for _ in range(MAX_COMMENT_DEPTH):
            current = CommunityComment.create_reply(
                parent=current, author_id=uuid4(), body=CommentBody("Nested reply.")
            )
        assert current.depth == MAX_COMMENT_DEPTH

        try:
            CommunityComment.create_reply(
                parent=current, author_id=uuid4(), body=CommentBody("One too deep.")
            )
            raised = False
        except MaxCommentDepthExceededError:
            raised = True
        assert raised is True

    def test_max_depth_error_references_the_parent_id(self) -> None:
        current = _comment()
        for _ in range(MAX_COMMENT_DEPTH):
            current = CommunityComment.create_reply(
                parent=current, author_id=uuid4(), body=CommentBody("Nested reply.")
            )

        try:
            CommunityComment.create_reply(
                parent=current, author_id=uuid4(), body=CommentBody("One too deep.")
            )
            error = None
        except MaxCommentDepthExceededError as e:
            error = e
        assert error is not None
        assert error.parent_comment_id == current.id
        assert error.max_depth == MAX_COMMENT_DEPTH


class TestCommunityCommentUpdateContent:
    def test_updates_the_body(self) -> None:
        comment = _comment()
        new_body = CommentBody("A brand new body.")
        comment.update_content(body=new_body)
        assert comment.body == new_body

    def test_no_arguments_leaves_fields_unchanged(self) -> None:
        comment = _comment()
        original_body = comment.body
        comment.update_content()
        assert comment.body == original_body

    def test_updates_updated_by(self) -> None:
        comment = _comment()
        updater_id = uuid4()
        comment.update_content(updated_by=updater_id)
        assert comment.updated_by == updater_id

    def test_updates_updated_at_timestamp(self) -> None:
        comment = _comment()
        before = comment.updated_at
        comment.update_content(body=CommentBody("New body."))
        assert comment.updated_at >= before

    def test_records_a_community_comment_updated_event(self) -> None:
        comment = _comment()
        comment.pull_events()
        comment.update_content(body=CommentBody("New body."))
        events = comment.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityCommentUpdated)
        assert events[0].comment_id == comment.id

    def test_editing_a_draft_body_creates_no_revision(self) -> None:
        comment = _comment()
        revision = comment.update_content(body=CommentBody("New body while still a draft."))
        assert revision is None

    def test_editing_a_draft_body_leaves_revision_number_unchanged(self) -> None:
        comment = _comment()
        comment.update_content(body=CommentBody("New body while still a draft."))
        assert comment.revision_number == 1

    def test_editing_a_published_comment_body_creates_a_revision(self) -> None:
        original_body = CommentBody("Original published body.")
        comment = _comment(body=original_body)
        comment.publish()
        revision = comment.update_content(body=CommentBody("Edited published body."))
        assert revision is not None
        assert revision.previous_body == str(original_body)

    def test_editing_a_published_comment_increments_revision_number(self) -> None:
        comment = _comment()
        comment.publish()
        comment.update_content(body=CommentBody("Edited body."))
        assert comment.revision_number == 2

    def test_editing_published_comment_with_unchanged_body_creates_no_revision(self) -> None:
        body = CommentBody("Same body throughout.")
        comment = _comment(body=body)
        comment.publish()
        revision = comment.update_content(body=CommentBody("Same body throughout."))
        assert revision is None

    def test_revision_author_defaults_to_the_comments_own_author(self) -> None:
        author_id = uuid4()
        comment = _comment(author_id=author_id)
        comment.publish()
        revision = comment.update_content(body=CommentBody("Edited body."))
        assert revision is not None
        assert revision.author_id == author_id

    def test_revision_author_uses_explicit_updated_by_when_given(self) -> None:
        editor_id = uuid4()
        comment = _comment()
        comment.publish()
        revision = comment.update_content(body=CommentBody("Edited body."), updated_by=editor_id)
        assert revision is not None
        assert revision.author_id == editor_id


class TestCommunityCommentPublish:
    def test_sets_status_to_published(self) -> None:
        comment = _comment()
        comment.publish()
        assert comment.status is CommentStatus.PUBLISHED

    def test_sets_published_at(self) -> None:
        comment = _comment()
        comment.publish()
        assert comment.published_at is not None

    def test_already_published_raises(self) -> None:
        comment = _comment()
        comment.publish()
        try:
            comment.publish()
            raised = False
        except CommentAlreadyPublishedError:
            raised = True
        assert raised is True

    def test_records_a_community_comment_published_event(self) -> None:
        comment = _comment()
        comment.pull_events()
        comment.publish()
        events = comment.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityCommentPublished)
        assert events[0].comment_id == comment.id

    def test_republishing_an_archived_comment_succeeds(self) -> None:
        comment = _comment()
        comment.publish()
        comment.archive()
        comment.publish()
        assert comment.status is CommentStatus.PUBLISHED


class TestCommunityCommentArchive:
    def test_sets_status_to_archived(self) -> None:
        comment = _comment()
        comment.archive()
        assert comment.status is CommentStatus.ARCHIVED

    def test_already_archived_raises(self) -> None:
        comment = _comment()
        comment.archive()
        try:
            comment.archive()
            raised = False
        except CommentAlreadyArchivedError:
            raised = True
        assert raised is True

    def test_records_a_community_comment_archived_event(self) -> None:
        comment = _comment()
        comment.pull_events()
        comment.archive()
        events = comment.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityCommentArchived)
        assert events[0].comment_id == comment.id

    def test_archiving_a_draft_comment_succeeds(self) -> None:
        comment = _comment()
        comment.archive()
        assert comment.status is CommentStatus.ARCHIVED

    def test_archiving_a_parent_does_not_change_its_replies_status(self) -> None:
        parent = _comment()
        parent.publish()
        reply = CommunityComment.create_reply(
            parent=parent, author_id=uuid4(), body=CommentBody("A reply.")
        )
        reply.publish()
        parent.archive()
        assert reply.status is CommentStatus.PUBLISHED


class TestCommunityCommentRestore:
    def test_restores_an_archived_comment_to_draft(self) -> None:
        comment = _comment()
        comment.archive()
        comment.restore()
        assert comment.status is CommentStatus.DRAFT

    def test_restores_a_deleted_comment_to_draft(self) -> None:
        comment = _comment()
        comment.delete()
        comment.restore()
        assert comment.status is CommentStatus.DRAFT

    def test_never_restores_directly_to_published(self) -> None:
        comment = _comment()
        comment.publish()
        comment.archive()
        comment.restore()
        assert comment.status is CommentStatus.DRAFT

    def test_restoring_a_draft_comment_raises(self) -> None:
        comment = _comment()
        try:
            comment.restore()
            raised = False
        except CommentCannotBeRestoredError:
            raised = True
        assert raised is True

    def test_restoring_a_published_comment_raises(self) -> None:
        comment = _comment()
        comment.publish()
        try:
            comment.restore()
            raised = False
        except CommentCannotBeRestoredError:
            raised = True
        assert raised is True

    def test_records_a_community_comment_restored_event(self) -> None:
        comment = _comment()
        comment.archive()
        comment.pull_events()
        comment.restore()
        events = comment.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityCommentRestored)
        assert events[0].comment_id == comment.id


class TestCommunityCommentDelete:
    def test_sets_status_to_deleted(self) -> None:
        comment = _comment()
        comment.delete()
        assert comment.status is CommentStatus.DELETED

    def test_already_deleted_raises(self) -> None:
        comment = _comment()
        comment.delete()
        try:
            comment.delete()
            raised = False
        except CommentAlreadyDeletedError:
            raised = True
        assert raised is True

    def test_records_a_community_comment_deleted_event(self) -> None:
        comment = _comment()
        comment.pull_events()
        comment.delete()
        events = comment.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityCommentDeleted)
        assert events[0].comment_id == comment.id

    def test_deleting_a_published_comment_succeeds(self) -> None:
        comment = _comment()
        comment.publish()
        comment.delete()
        assert comment.status is CommentStatus.DELETED

    def test_deleting_a_parent_does_not_change_its_replies_status(self) -> None:
        parent = _comment()
        parent.publish()
        reply = CommunityComment.create_reply(
            parent=parent, author_id=uuid4(), body=CommentBody("A reply.")
        )
        reply.publish()
        parent.delete()
        assert reply.status is CommentStatus.PUBLISHED
