"""Unit tests for `ListCommentsService` — cursor-paginated, top-level-only,
published-only feed of one target's own comments."""

from uuid import uuid4

from app.modules.community_comments.application.dto import ListCommentsInput
from app.modules.community_comments.application.services.list_comments_service import (
    ListCommentsService,
)
from app.modules.community_comments.domain.entities import CommunityComment
from app.modules.community_comments.domain.enums import CommentTargetType
from app.modules.community_comments.domain.value_objects import CommentBody
from tests.unit.modules.community_comments.application.fakes import FakeCommunityCommentRepository


def _make_published_comment(**overrides: object) -> CommunityComment:
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


class TestListComments:
    async def test_returns_only_published_top_level_comments_for_the_target(self) -> None:
        comments = FakeCommunityCommentRepository()
        service = ListCommentsService(comment_repository=comments)
        org_id, target_id = uuid4(), uuid4()
        published = _make_published_comment(
            organization_id=org_id, target_type=CommentTargetType.POST, target_id=target_id
        )
        draft = CommunityComment.create(
            target_type=CommentTargetType.POST,
            target_id=target_id,
            community_id=uuid4(),
            organization_id=org_id,
            topic_id=None,
            author_id=uuid4(),
            body=CommentBody("Draft."),
        )
        reply = CommunityComment.create_reply(
            parent=published, author_id=uuid4(), body=CommentBody("A reply.")
        )
        reply.publish()
        other_target = _make_published_comment(organization_id=org_id)
        await comments.add(published)
        await comments.add(draft)
        await comments.add(reply)
        await comments.add(other_target)

        result = await service.list_comments(
            ListCommentsInput(
                organization_id=org_id, target_type=CommentTargetType.POST, target_id=target_id
            )
        )
        assert [i.comment_id for i in result.items] == [published.id]

    async def test_masks_anonymous_authors_in_the_feed(self) -> None:
        comments = FakeCommunityCommentRepository()
        service = ListCommentsService(comment_repository=comments)
        org_id, target_id = uuid4(), uuid4()
        anonymous = _make_published_comment(
            organization_id=org_id, target_id=target_id, is_anonymous=True
        )
        await comments.add(anonymous)

        result = await service.list_comments(
            ListCommentsInput(
                organization_id=org_id, target_type=CommentTargetType.POST, target_id=target_id
            )
        )
        assert result.items[0].author_id is None

    async def test_returns_a_next_cursor_when_more_results_remain(self) -> None:
        comments = FakeCommunityCommentRepository()
        service = ListCommentsService(comment_repository=comments)
        org_id, target_id = uuid4(), uuid4()
        for _ in range(3):
            await comments.add(_make_published_comment(organization_id=org_id, target_id=target_id))

        result = await service.list_comments(
            ListCommentsInput(
                organization_id=org_id,
                target_type=CommentTargetType.POST,
                target_id=target_id,
                limit=2,
            )
        )
        assert len(result.items) == 2
        assert result.next_cursor is not None

    async def test_scoped_to_organization(self) -> None:
        comments = FakeCommunityCommentRepository()
        service = ListCommentsService(comment_repository=comments)
        org_id, target_id = uuid4(), uuid4()
        matching = _make_published_comment(organization_id=org_id, target_id=target_id)
        other_org = _make_published_comment(target_id=target_id)
        await comments.add(matching)
        await comments.add(other_org)

        result = await service.list_comments(
            ListCommentsInput(
                organization_id=org_id, target_type=CommentTargetType.POST, target_id=target_id
            )
        )
        assert [i.comment_id for i in result.items] == [matching.id]

    async def test_no_next_cursor_when_everything_fits_on_one_page(self) -> None:
        comments = FakeCommunityCommentRepository()
        service = ListCommentsService(comment_repository=comments)
        org_id, target_id = uuid4(), uuid4()
        await comments.add(_make_published_comment(organization_id=org_id, target_id=target_id))

        result = await service.list_comments(
            ListCommentsInput(
                organization_id=org_id, target_type=CommentTargetType.POST, target_id=target_id
            )
        )
        assert result.next_cursor is None

    async def test_cursor_fetches_the_next_page(self) -> None:
        comments = FakeCommunityCommentRepository()
        service = ListCommentsService(comment_repository=comments)
        org_id, target_id = uuid4(), uuid4()
        for _ in range(3):
            await comments.add(_make_published_comment(organization_id=org_id, target_id=target_id))

        first_page = await service.list_comments(
            ListCommentsInput(
                organization_id=org_id,
                target_type=CommentTargetType.POST,
                target_id=target_id,
                limit=2,
            )
        )
        second_page = await service.list_comments(
            ListCommentsInput(
                organization_id=org_id,
                target_type=CommentTargetType.POST,
                target_id=target_id,
                limit=2,
                cursor=first_page.next_cursor,
            )
        )
        first_ids = {i.comment_id for i in first_page.items}
        second_ids = {i.comment_id for i in second_page.items}
        assert first_ids.isdisjoint(second_ids)
