"""Unit tests for `GetThreadService` — the entire bounded-depth
conversation rooted at one comment, fetched flat, non-recursively."""

from uuid import uuid4

from app.modules.community_comments.application.services.get_thread_service import (
    GetThreadService,
)
from app.modules.community_comments.domain.entities import CommunityComment
from app.modules.community_comments.domain.enums import CommentTargetType
from app.modules.community_comments.domain.value_objects import CommentBody
from tests.unit.modules.community_comments.application.fakes import FakeCommunityCommentRepository


def _make_published_root(**overrides: object) -> CommunityComment:
    defaults: dict[str, object] = {
        "target_type": CommentTargetType.POST,
        "target_id": uuid4(),
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "topic_id": None,
        "author_id": uuid4(),
        "body": CommentBody("Root body."),
    }
    defaults.update(overrides)
    comment = CommunityComment.create(**defaults)  # type: ignore[arg-type]
    comment.publish()
    return comment


class TestGetThread:
    async def test_includes_the_root_itself(self) -> None:
        comments = FakeCommunityCommentRepository()
        service = GetThreadService(comment_repository=comments)
        root = _make_published_root()
        await comments.add(root)

        result = await service.get_thread(root.id)
        assert [i.comment_id for i in result.items] == [root.id]

    async def test_includes_nested_replies_up_to_the_default_max_depth(self) -> None:
        comments = FakeCommunityCommentRepository()
        service = GetThreadService(comment_repository=comments)
        root = _make_published_root()
        await comments.add(root)

        current = root
        chain = [root]
        for _ in range(3):
            reply = CommunityComment.create_reply(
                parent=current, author_id=uuid4(), body=CommentBody("Reply.")
            )
            reply.publish()
            await comments.add(reply)
            chain.append(reply)
            current = reply

        result = await service.get_thread(root.id)
        assert {i.comment_id for i in result.items} == {c.id for c in chain}

    async def test_excludes_replies_beyond_max_depth(self) -> None:
        comments = FakeCommunityCommentRepository()
        service = GetThreadService(comment_repository=comments)
        root = _make_published_root()
        await comments.add(root)

        result = await service.get_thread(root.id, max_depth=0)
        assert [i.comment_id for i in result.items] == [root.id]

        reply = CommunityComment.create_reply(
            parent=root, author_id=uuid4(), body=CommentBody("Reply.")
        )
        reply.publish()
        await comments.add(reply)

        result_at_zero = await service.get_thread(root.id, max_depth=0)
        assert reply.id not in {i.comment_id for i in result_at_zero.items}

        result_at_one = await service.get_thread(root.id, max_depth=1)
        assert reply.id in {i.comment_id for i in result_at_one.items}

    async def test_excludes_draft_replies(self) -> None:
        comments = FakeCommunityCommentRepository()
        service = GetThreadService(comment_repository=comments)
        root = _make_published_root()
        await comments.add(root)
        draft_reply = CommunityComment.create_reply(
            parent=root, author_id=uuid4(), body=CommentBody("Draft reply.")
        )
        await comments.add(draft_reply)

        result = await service.get_thread(root.id)
        assert draft_reply.id not in {i.comment_id for i in result.items}

    async def test_orders_by_depth_then_created_at(self) -> None:
        comments = FakeCommunityCommentRepository()
        service = GetThreadService(comment_repository=comments)
        root = _make_published_root()
        await comments.add(root)
        first_reply = CommunityComment.create_reply(
            parent=root, author_id=uuid4(), body=CommentBody("First.")
        )
        first_reply.publish()
        await comments.add(first_reply)
        second_reply = CommunityComment.create_reply(
            parent=first_reply, author_id=uuid4(), body=CommentBody("Second.")
        )
        second_reply.publish()
        await comments.add(second_reply)

        result = await service.get_thread(root.id)
        depths = [i.depth for i in result.items]
        assert depths == sorted(depths)
