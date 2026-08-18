"""Unit tests for `GetCommentService` — the one read path this module
enforces comment-level viewability on; every other read path is already
restricted to `PUBLISHED` comments by its own repository query."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityMemberStatus, CommunityRole
from app.modules.community_comments.application.services.comment_query_service import (
    GetCommentService,
)
from app.modules.community_comments.domain.entities import CommunityComment
from app.modules.community_comments.domain.enums import CommentTargetType
from app.modules.community_comments.domain.exceptions import CommentNotViewableError
from app.modules.community_comments.domain.value_objects import CommentBody
from tests.unit.modules.community_comments.application.fakes import (
    FakeCommunityCommentRepository,
    FakeCommunityQueryPort,
    make_member_summary,
)


def _make_comment(**overrides: object) -> CommunityComment:
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
    return CommunityComment.create(**defaults)  # type: ignore[arg-type]


class TestGetCommentById:
    async def test_returns_none_for_unknown_comment(self) -> None:
        comments = FakeCommunityCommentRepository()
        communities = FakeCommunityQueryPort()
        service = GetCommentService(comment_repository=comments, community_query_port=communities)

        result = await service.get_by_id(uuid4())
        assert result is None

    async def test_returns_a_published_comment_with_no_acting_user(self) -> None:
        comments = FakeCommunityCommentRepository()
        communities = FakeCommunityQueryPort()
        comment = _make_comment()
        comment.publish()
        await comments.add(comment)
        service = GetCommentService(comment_repository=comments, community_query_port=communities)

        result = await service.get_by_id(comment.id)
        assert result is not None
        assert result.comment_id == comment.id

    async def test_masks_author_id_for_an_anonymous_comment(self) -> None:
        comments = FakeCommunityCommentRepository()
        communities = FakeCommunityQueryPort()
        comment = _make_comment(is_anonymous=True)
        comment.publish()
        await comments.add(comment)
        service = GetCommentService(comment_repository=comments, community_query_port=communities)

        result = await service.get_by_id(comment.id, acting_user_id=comment.author_id)
        assert result is not None
        assert result.author_id is None

    async def test_does_not_mask_author_id_for_a_non_anonymous_comment(self) -> None:
        comments = FakeCommunityCommentRepository()
        communities = FakeCommunityQueryPort()
        comment = _make_comment(is_anonymous=False)
        comment.publish()
        await comments.add(comment)
        service = GetCommentService(comment_repository=comments, community_query_port=communities)

        result = await service.get_by_id(comment.id)
        assert result is not None
        assert result.author_id == comment.author_id

    async def test_raises_when_a_draft_comment_is_viewed_by_a_stranger(self) -> None:
        comments = FakeCommunityCommentRepository()
        communities = FakeCommunityQueryPort()
        comment = _make_comment()
        await comments.add(comment)
        service = GetCommentService(comment_repository=comments, community_query_port=communities)

        with pytest.raises(CommentNotViewableError):
            await service.get_by_id(comment.id, acting_user_id=uuid4())

    async def test_draft_comment_viewable_by_its_own_author(self) -> None:
        comments = FakeCommunityCommentRepository()
        communities = FakeCommunityQueryPort()
        comment = _make_comment()
        await comments.add(comment)
        service = GetCommentService(comment_repository=comments, community_query_port=communities)

        result = await service.get_by_id(comment.id, acting_user_id=comment.author_id)
        assert result is not None

    async def test_draft_comment_viewable_by_a_moderator(self) -> None:
        comments = FakeCommunityCommentRepository()
        communities = FakeCommunityQueryPort()
        comment = _make_comment()
        await comments.add(comment)
        moderator_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=comment.community_id,
                user_id=moderator_id,
                role=CommunityRole.MODERATOR,
                status=CommunityMemberStatus.ACTIVE,
            )
        )
        service = GetCommentService(comment_repository=comments, community_query_port=communities)

        result = await service.get_by_id(comment.id, acting_user_id=moderator_id)
        assert result is not None

    async def test_draft_comment_not_viewable_by_a_plain_member(self) -> None:
        comments = FakeCommunityCommentRepository()
        communities = FakeCommunityQueryPort()
        comment = _make_comment()
        await comments.add(comment)
        viewer_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=comment.community_id, user_id=viewer_id, role=CommunityRole.MEMBER
            )
        )
        service = GetCommentService(comment_repository=comments, community_query_port=communities)

        with pytest.raises(CommentNotViewableError):
            await service.get_by_id(comment.id, acting_user_id=viewer_id)
