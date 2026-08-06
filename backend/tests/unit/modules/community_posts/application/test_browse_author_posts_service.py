"""Unit tests for `BrowseAuthorPostsService`, using in-memory fakes."""

from uuid import uuid4

from app.modules.community_posts.application.dto import BrowseAuthorPostsInput
from app.modules.community_posts.application.services.browse_author_posts_service import (
    BrowseAuthorPostsService,
)
from app.modules.community_posts.domain.entities import CommunityPost
from app.modules.community_posts.domain.value_objects import PostTitle
from tests.unit.modules.community_posts.application.fakes import FakeCommunityPostRepository


def _make_published_post(*, organization_id: object, author_id: object) -> CommunityPost:
    post = CommunityPost.create(
        community_id=uuid4(),
        organization_id=organization_id,  # type: ignore[arg-type]
        author_id=author_id,  # type: ignore[arg-type]
        title=PostTitle("Title"),
        body="Body",
    )
    post.publish()
    return post


class TestBrowseAuthorPosts:
    async def test_returns_only_the_given_authors_posts(self) -> None:
        posts = FakeCommunityPostRepository()
        service = BrowseAuthorPostsService(post_repository=posts)
        org_id, author_id = uuid4(), uuid4()
        matching = _make_published_post(organization_id=org_id, author_id=author_id)
        other_author = _make_published_post(organization_id=org_id, author_id=uuid4())
        await posts.add(matching)
        await posts.add(other_author)

        result = await service.browse(
            BrowseAuthorPostsInput(organization_id=org_id, author_id=author_id)
        )
        assert [item.post_id for item in result.items] == [matching.id]

    async def test_excludes_unpublished_posts(self) -> None:
        posts = FakeCommunityPostRepository()
        service = BrowseAuthorPostsService(post_repository=posts)
        org_id, author_id = uuid4(), uuid4()
        published = _make_published_post(organization_id=org_id, author_id=author_id)
        draft = CommunityPost.create(
            community_id=uuid4(),
            organization_id=org_id,
            author_id=author_id,
            title=PostTitle("Draft"),
            body="Body",
        )
        await posts.add(published)
        await posts.add(draft)

        result = await service.browse(
            BrowseAuthorPostsInput(organization_id=org_id, author_id=author_id)
        )
        assert [item.post_id for item in result.items] == [published.id]

    async def test_scopes_to_organization(self) -> None:
        posts = FakeCommunityPostRepository()
        service = BrowseAuthorPostsService(post_repository=posts)
        org_id, author_id = uuid4(), uuid4()
        matching = _make_published_post(organization_id=org_id, author_id=author_id)
        other_org = _make_published_post(organization_id=uuid4(), author_id=author_id)
        await posts.add(matching)
        await posts.add(other_org)

        result = await service.browse(
            BrowseAuthorPostsInput(organization_id=org_id, author_id=author_id)
        )
        assert [item.post_id for item in result.items] == [matching.id]

    async def test_empty_feed_returns_no_items_and_no_cursor(self) -> None:
        posts = FakeCommunityPostRepository()
        service = BrowseAuthorPostsService(post_repository=posts)

        result = await service.browse(
            BrowseAuthorPostsInput(organization_id=uuid4(), author_id=uuid4())
        )
        assert result.items == ()
        assert result.next_cursor is None

    async def test_respects_limit(self) -> None:
        posts = FakeCommunityPostRepository()
        service = BrowseAuthorPostsService(post_repository=posts)
        org_id, author_id = uuid4(), uuid4()
        for _ in range(3):
            await posts.add(_make_published_post(organization_id=org_id, author_id=author_id))

        result = await service.browse(
            BrowseAuthorPostsInput(organization_id=org_id, author_id=author_id, limit=2)
        )
        assert len(result.items) == 2
        assert result.next_cursor is not None

    async def test_cursor_pagination_covers_all_posts_without_duplicates(self) -> None:
        posts = FakeCommunityPostRepository()
        service = BrowseAuthorPostsService(post_repository=posts)
        org_id, author_id = uuid4(), uuid4()
        created = [
            _make_published_post(organization_id=org_id, author_id=author_id) for _ in range(5)
        ]
        for post in created:
            await posts.add(post)

        seen: list[object] = []
        cursor: str | None = None
        for _ in range(10):
            page = await service.browse(
                BrowseAuthorPostsInput(
                    organization_id=org_id, author_id=author_id, cursor=cursor, limit=2
                )
            )
            seen.extend(item.post_id for item in page.items)
            cursor = page.next_cursor
            if cursor is None:
                break

        assert sorted(seen, key=str) == sorted((p.id for p in created), key=str)
        assert len(seen) == len(set(seen))
