"""Unit tests for `SearchPostsService`, using in-memory fakes."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.modules.community_posts.application.dto import SearchPostsInput
from app.modules.community_posts.application.services.search_posts_service import (
    SearchPostsService,
)
from app.modules.community_posts.domain.entities import CommunityPost
from app.modules.community_posts.domain.enums import PostStatus, PostType, PostVisibility
from app.modules.community_posts.domain.value_objects import PostTitle
from tests.unit.modules.community_posts.application.fakes import FakeCommunityPostRepository


def _make_post(**overrides: object) -> CommunityPost:
    defaults: dict[str, object] = {
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "author_id": uuid4(),
        "title": PostTitle("Title"),
        "body": "Body",
    }
    defaults.update(overrides)
    return CommunityPost.create(**defaults)  # type: ignore[arg-type]


class TestSearchPosts:
    async def test_matches_a_keyword_in_the_title(self) -> None:
        posts = FakeCommunityPostRepository()
        service = SearchPostsService(post_repository=posts)
        org_id = uuid4()
        matching = _make_post(organization_id=org_id, title=PostTitle("Managing Diabetes"))
        other = _make_post(organization_id=org_id, title=PostTitle("Unrelated Topic"))
        await posts.add(matching)
        await posts.add(other)

        result = await service.search(SearchPostsInput(organization_id=org_id, query="diabetes"))
        assert result.total == 1
        assert result.items[0].post_id == matching.id

    async def test_scopes_to_organization(self) -> None:
        posts = FakeCommunityPostRepository()
        service = SearchPostsService(post_repository=posts)
        org_id = uuid4()
        matching = _make_post(organization_id=org_id, title=PostTitle("Shared Term"))
        other_org = _make_post(title=PostTitle("Shared Term"))
        await posts.add(matching)
        await posts.add(other_org)

        result = await service.search(SearchPostsInput(organization_id=org_id, query="Shared"))
        assert result.total == 1
        assert result.items[0].post_id == matching.id

    async def test_no_match_returns_empty(self) -> None:
        posts = FakeCommunityPostRepository()
        service = SearchPostsService(post_repository=posts)
        org_id = uuid4()
        await posts.add(_make_post(organization_id=org_id, title=PostTitle("Something Else")))

        result = await service.search(
            SearchPostsInput(organization_id=org_id, query="zzz-no-match")
        )
        assert result.total == 0
        assert result.items == ()

    async def test_filters_by_community(self) -> None:
        posts = FakeCommunityPostRepository()
        service = SearchPostsService(post_repository=posts)
        org_id, community_id = uuid4(), uuid4()
        matching = _make_post(organization_id=org_id, community_id=community_id)
        other = _make_post(organization_id=org_id)
        await posts.add(matching)
        await posts.add(other)

        result = await service.search(
            SearchPostsInput(organization_id=org_id, query="", community_id=community_id)
        )
        assert [i.post_id for i in result.items] == [matching.id]

    async def test_filters_by_author(self) -> None:
        posts = FakeCommunityPostRepository()
        service = SearchPostsService(post_repository=posts)
        org_id, author_id = uuid4(), uuid4()
        matching = _make_post(organization_id=org_id, author_id=author_id)
        other = _make_post(organization_id=org_id)
        await posts.add(matching)
        await posts.add(other)

        result = await service.search(
            SearchPostsInput(organization_id=org_id, query="", author_id=author_id)
        )
        assert [i.post_id for i in result.items] == [matching.id]

    async def test_filters_by_post_type(self) -> None:
        posts = FakeCommunityPostRepository()
        service = SearchPostsService(post_repository=posts)
        org_id = uuid4()
        matching = _make_post(organization_id=org_id, post_type=PostType.RESEARCH)
        other = _make_post(organization_id=org_id, post_type=PostType.DISCUSSION)
        await posts.add(matching)
        await posts.add(other)

        result = await service.search(
            SearchPostsInput(organization_id=org_id, query="", post_type=(PostType.RESEARCH,))
        )
        assert [i.post_id for i in result.items] == [matching.id]

    async def test_filters_by_status(self) -> None:
        posts = FakeCommunityPostRepository()
        service = SearchPostsService(post_repository=posts)
        org_id = uuid4()
        published = _make_post(organization_id=org_id)
        published.publish()
        draft = _make_post(organization_id=org_id)
        await posts.add(published)
        await posts.add(draft)

        result = await service.search(
            SearchPostsInput(organization_id=org_id, query="", status=(PostStatus.PUBLISHED,))
        )
        assert [i.post_id for i in result.items] == [published.id]

    async def test_filters_by_visibility(self) -> None:
        posts = FakeCommunityPostRepository()
        service = SearchPostsService(post_repository=posts)
        org_id = uuid4()
        matching = _make_post(organization_id=org_id, visibility=PostVisibility.PRIVATE)
        other = _make_post(organization_id=org_id, visibility=PostVisibility.PUBLIC)
        await posts.add(matching)
        await posts.add(other)

        result = await service.search(
            SearchPostsInput(organization_id=org_id, query="", visibility=(PostVisibility.PRIVATE,))
        )
        assert [i.post_id for i in result.items] == [matching.id]

    async def test_filters_pinned_only(self) -> None:
        posts = FakeCommunityPostRepository()
        service = SearchPostsService(post_repository=posts)
        org_id = uuid4()
        pinned = _make_post(organization_id=org_id)
        pinned.set_pinned(True)
        other = _make_post(organization_id=org_id)
        await posts.add(pinned)
        await posts.add(other)

        result = await service.search(
            SearchPostsInput(organization_id=org_id, query="", pinned_only=True)
        )
        assert [i.post_id for i in result.items] == [pinned.id]

    async def test_filters_featured_only(self) -> None:
        posts = FakeCommunityPostRepository()
        service = SearchPostsService(post_repository=posts)
        org_id = uuid4()
        featured = _make_post(organization_id=org_id)
        featured.set_featured(True)
        other = _make_post(organization_id=org_id)
        await posts.add(featured)
        await posts.add(other)

        result = await service.search(
            SearchPostsInput(organization_id=org_id, query="", featured_only=True)
        )
        assert [i.post_id for i in result.items] == [featured.id]

    async def test_respects_limit_and_offset(self) -> None:
        posts = FakeCommunityPostRepository()
        service = SearchPostsService(post_repository=posts)
        org_id = uuid4()
        for _ in range(3):
            await posts.add(_make_post(organization_id=org_id))

        first_page = await service.search(
            SearchPostsInput(organization_id=org_id, query="", limit=2, offset=0)
        )
        second_page = await service.search(
            SearchPostsInput(organization_id=org_id, query="", limit=2, offset=2)
        )
        assert first_page.total == 3
        assert len(first_page.items) == 2
        assert len(second_page.items) == 1

    async def test_filters_by_created_date_range(self) -> None:
        posts = FakeCommunityPostRepository()
        service = SearchPostsService(post_repository=posts)
        org_id = uuid4()
        post = _make_post(organization_id=org_id)
        await posts.add(post)
        now = datetime.now(UTC)

        in_range = await service.search(
            SearchPostsInput(
                organization_id=org_id,
                query="",
                created_from=now - timedelta(days=1),
                created_to=now + timedelta(days=1),
            )
        )
        out_of_range = await service.search(
            SearchPostsInput(organization_id=org_id, query="", created_from=now + timedelta(days=1))
        )
        assert [i.post_id for i in in_range.items] == [post.id]
        assert out_of_range.items == ()
