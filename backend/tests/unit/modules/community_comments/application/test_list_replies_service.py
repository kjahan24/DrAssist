"""Unit tests for `ListRepliesService` — cursor-paginated, direct-child-only
feed of one parent comment's own replies."""

from uuid import uuid4

from app.modules.community_comments.application.dto import ListRepliesInput
from app.modules.community_comments.application.services.list_replies_service import (
    ListRepliesService,
)
from app.modules.community_comments.domain.entities import CommunityComment
from app.modules.community_comments.domain.enums import CommentTargetType
from app.modules.community_comments.domain.value_objects import CommentBody
from tests.unit.modules.community_comments.application.fakes import FakeCommunityCommentRepository


def _make_published_parent(**overrides: object) -> CommunityComment:
    defaults: dict[str, object] = {
        "target_type": CommentTargetType.POST,
        "target_id": uuid4(),
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "topic_id": None,
        "author_id": uuid4(),
        "body": CommentBody("Body."),
    }
    defaults.update(overrides)
    comment = CommunityComment.create(**defaults)  # type: ignore[arg-type]
    comment.publish()
    return comment


class TestListReplies:
    async def test_returns_only_direct_published_replies(self) -> None:
        comments = FakeCommunityCommentRepository()
        service = ListRepliesService(comment_repository=comments)
        org_id = uuid4()
        parent = _make_published_parent(organization_id=org_id)
        direct_reply = CommunityComment.create_reply(
            parent=parent, author_id=uuid4(), body=CommentBody("Direct reply.")
        )
        direct_reply.publish()
        nested_reply = CommunityComment.create_reply(
            parent=direct_reply, author_id=uuid4(), body=CommentBody("Nested reply.")
        )
        nested_reply.publish()
        await comments.add(parent)
        await comments.add(direct_reply)
        await comments.add(nested_reply)

        result = await service.list_replies(
            ListRepliesInput(organization_id=org_id, parent_comment_id=parent.id)
        )
        assert [i.comment_id for i in result.items] == [direct_reply.id]

    async def test_excludes_draft_replies(self) -> None:
        comments = FakeCommunityCommentRepository()
        service = ListRepliesService(comment_repository=comments)
        org_id = uuid4()
        parent = _make_published_parent(organization_id=org_id)
        draft_reply = CommunityComment.create_reply(
            parent=parent, author_id=uuid4(), body=CommentBody("Draft reply.")
        )
        await comments.add(parent)
        await comments.add(draft_reply)

        result = await service.list_replies(
            ListRepliesInput(organization_id=org_id, parent_comment_id=parent.id)
        )
        assert result.items == ()

    async def test_masks_anonymous_authors(self) -> None:
        comments = FakeCommunityCommentRepository()
        service = ListRepliesService(comment_repository=comments)
        org_id = uuid4()
        parent = _make_published_parent(organization_id=org_id)
        reply = CommunityComment.create_reply(
            parent=parent, author_id=uuid4(), body=CommentBody("Reply."), is_anonymous=True
        )
        reply.publish()
        await comments.add(parent)
        await comments.add(reply)

        result = await service.list_replies(
            ListRepliesInput(organization_id=org_id, parent_comment_id=parent.id)
        )
        assert result.items[0].author_id is None

    async def test_returns_a_next_cursor_when_more_results_remain(self) -> None:
        comments = FakeCommunityCommentRepository()
        service = ListRepliesService(comment_repository=comments)
        org_id = uuid4()
        parent = _make_published_parent(organization_id=org_id)
        await comments.add(parent)
        for _ in range(3):
            reply = CommunityComment.create_reply(
                parent=parent, author_id=uuid4(), body=CommentBody("Reply.")
            )
            reply.publish()
            await comments.add(reply)

        result = await service.list_replies(
            ListRepliesInput(organization_id=org_id, parent_comment_id=parent.id, limit=2)
        )
        assert len(result.items) == 2
        assert result.next_cursor is not None

    async def test_returns_empty_for_a_parent_with_no_replies(self) -> None:
        comments = FakeCommunityCommentRepository()
        service = ListRepliesService(comment_repository=comments)
        org_id = uuid4()
        parent = _make_published_parent(organization_id=org_id)
        await comments.add(parent)

        result = await service.list_replies(
            ListRepliesInput(organization_id=org_id, parent_comment_id=parent.id)
        )
        assert result.items == ()
        assert result.next_cursor is None

    async def test_only_returns_replies_for_the_requested_parent(self) -> None:
        comments = FakeCommunityCommentRepository()
        service = ListRepliesService(comment_repository=comments)
        org_id = uuid4()
        parent_one = _make_published_parent(organization_id=org_id)
        parent_two = _make_published_parent(organization_id=org_id)
        await comments.add(parent_one)
        await comments.add(parent_two)
        reply_to_one = CommunityComment.create_reply(
            parent=parent_one, author_id=uuid4(), body=CommentBody("Reply to one.")
        )
        reply_to_one.publish()
        reply_to_two = CommunityComment.create_reply(
            parent=parent_two, author_id=uuid4(), body=CommentBody("Reply to two.")
        )
        reply_to_two.publish()
        await comments.add(reply_to_one)
        await comments.add(reply_to_two)

        result = await service.list_replies(
            ListRepliesInput(organization_id=org_id, parent_comment_id=parent_one.id)
        )
        assert [i.comment_id for i in result.items] == [reply_to_one.id]
