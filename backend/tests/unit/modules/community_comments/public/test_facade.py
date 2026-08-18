"""Unit tests for `CommentFacade` — exercised through `CommentQueryPort`
exactly as a future consumer module (Votes/Notifications/Moderation/AI
Analysis/...) would call it, per
`docs/backend-architecture/12_testing_architecture.md`'s "Contract
tests" framing."""

from uuid import uuid4

from app.modules.community_comments.domain.entities import CommunityComment
from app.modules.community_comments.domain.enums import CommentTargetType
from app.modules.community_comments.domain.value_objects import CommentBody
from app.modules.community_comments.public.facade import CommentFacade
from app.modules.community_comments.public.interfaces import CommentQueryPort
from tests.unit.modules.community_comments.application.fakes import (
    FakeCommunityCommentRepository,
)


def _facade() -> tuple[CommentFacade, FakeCommunityCommentRepository]:
    comments = FakeCommunityCommentRepository()
    facade = CommentFacade(comment_repository=comments)
    return facade, comments


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


class TestCommentFacade:
    def test_is_a_comment_query_port(self) -> None:
        facade, _ = _facade()
        assert isinstance(facade, CommentQueryPort)

    async def test_comment_exists_true_when_present(self) -> None:
        facade, comments = _facade()
        comment = _make_comment()
        await comments.add(comment)

        assert await facade.comment_exists(comment.id) is True

    async def test_comment_exists_false_when_absent(self) -> None:
        facade, _ = _facade()
        assert await facade.comment_exists(uuid4()) is False

    async def test_get_comment_summary_returns_a_summary_when_present(self) -> None:
        facade, comments = _facade()
        comment = _make_comment()
        await comments.add(comment)

        summary = await facade.get_comment_summary(comment.id)

        assert summary is not None
        assert summary.comment_id == comment.id

    async def test_get_comment_summary_returns_none_for_unknown_id(self) -> None:
        facade, _ = _facade()
        assert await facade.get_comment_summary(uuid4()) is None

    async def test_get_comment_summary_reflects_the_comments_current_body(self) -> None:
        facade, comments = _facade()
        comment = _make_comment(body=CommentBody("Original body."))
        await comments.add(comment)
        comment.update_content(body=CommentBody("Edited body."))

        summary = await facade.get_comment_summary(comment.id)
        assert summary is not None
        assert summary.body == "Edited body."

    async def test_get_comment_summary_masks_the_author_id_for_an_anonymous_comment(self) -> None:
        facade, comments = _facade()
        comment = _make_comment(is_anonymous=True)
        await comments.add(comment)

        summary = await facade.get_comment_summary(comment.id)
        assert summary is not None
        assert summary.author_id is None

    async def test_get_comment_summary_does_not_enforce_viewability(self) -> None:
        """Module-to-module facade reads have no acting user, so
        `_authorization.ensure_can_view` (an end-user-facing rule) does
        not apply here — see `CommentFacade`'s own docstring."""
        facade, comments = _facade()
        comment = _make_comment()
        await comments.add(comment)

        summary = await facade.get_comment_summary(comment.id)
        assert summary is not None
