"""Unit tests for `PostFacade` — exercised through `PostQueryPort` exactly
as a future consumer module (Questions/Answers/Comments/AI Summary/...)
would call it, per
`docs/backend-architecture/12_testing_architecture.md`'s "Contract
tests" framing."""

from uuid import uuid4

from app.modules.community_posts.domain.entities import CommunityPost
from app.modules.community_posts.domain.enums import PostVisibility
from app.modules.community_posts.domain.value_objects import PostTitle
from app.modules.community_posts.public.facade import PostFacade
from app.modules.community_posts.public.interfaces import PostQueryPort
from tests.unit.modules.community_posts.application.fakes import FakeCommunityPostRepository


def _facade() -> tuple[PostFacade, FakeCommunityPostRepository]:
    posts = FakeCommunityPostRepository()
    facade = PostFacade(post_repository=posts)
    return facade, posts


class TestPostFacade:
    def test_is_a_post_query_port(self) -> None:
        facade, _ = _facade()
        assert isinstance(facade, PostQueryPort)

    async def test_post_exists_true_when_present(self) -> None:
        facade, posts = _facade()
        post = CommunityPost.create(
            community_id=uuid4(),
            organization_id=uuid4(),
            author_id=uuid4(),
            title=PostTitle("Title"),
            body="Body",
        )
        await posts.add(post)

        assert await facade.post_exists(post.id) is True

    async def test_post_exists_false_when_absent(self) -> None:
        facade, _ = _facade()
        assert await facade.post_exists(uuid4()) is False

    async def test_get_post_summary_returns_a_summary_when_present(self) -> None:
        facade, posts = _facade()
        post = CommunityPost.create(
            community_id=uuid4(),
            organization_id=uuid4(),
            author_id=uuid4(),
            title=PostTitle("Title"),
            body="Body",
        )
        await posts.add(post)

        summary = await facade.get_post_summary(post.id)

        assert summary is not None
        assert summary.post_id == post.id

    async def test_get_post_summary_returns_none_for_unknown_id(self) -> None:
        facade, _ = _facade()
        assert await facade.get_post_summary(uuid4()) is None

    async def test_get_post_summary_reflects_the_posts_current_title(self) -> None:
        facade, posts = _facade()
        post = CommunityPost.create(
            community_id=uuid4(),
            organization_id=uuid4(),
            author_id=uuid4(),
            title=PostTitle("Original Title"),
            body="Body",
        )
        await posts.add(post)
        post.update_content(title=PostTitle("Renamed Title"))

        summary = await facade.get_post_summary(post.id)
        assert summary is not None
        assert summary.title == "Renamed Title"

    async def test_get_post_summary_does_not_enforce_visibility(self) -> None:
        """Module-to-module facade reads have no acting user, so
        `PostVisibility` (an end-user-facing rule) does not apply here —
        see `PostFacade`'s own docstring."""
        facade, posts = _facade()
        post = CommunityPost.create(
            community_id=uuid4(),
            organization_id=uuid4(),
            author_id=uuid4(),
            title=PostTitle("Title"),
            body="Body",
            visibility=PostVisibility.PRIVATE,
        )
        await posts.add(post)

        summary = await facade.get_post_summary(post.id)
        assert summary is not None
