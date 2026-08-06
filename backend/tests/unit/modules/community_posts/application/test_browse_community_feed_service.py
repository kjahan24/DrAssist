"""Unit tests for `BrowseCommunityFeedService`, using in-memory fakes.

Covers the `pinned_first=True` behavior (pinned posts surfaced once on
page 1 only) and cursor pagination across multiple pages — see
`CommunityPostRepository.browse_feed`'s own docstring for the contract
these tests are pinned against.
"""

from uuid import uuid4

import pytest

from app.modules.community_posts.application.dto import BrowseCommunityFeedInput
from app.modules.community_posts.application.services.browse_community_feed_service import (
    BrowseCommunityFeedService,
)
from app.modules.community_posts.domain.entities import CommunityPost
from app.modules.community_posts.domain.exceptions import CommunityNotFoundForPostError
from app.modules.community_posts.domain.value_objects import PostTitle
from tests.unit.modules.community_posts.application.fakes import (
    FakeCommunityPostRepository,
    FakeCommunityQueryPort,
    make_community_summary,
)


def _make_published_post(*, community_id: object, organization_id: object) -> CommunityPost:
    post = CommunityPost.create(
        community_id=community_id,  # type: ignore[arg-type]
        organization_id=organization_id,  # type: ignore[arg-type]
        author_id=uuid4(),
        title=PostTitle("Title"),
        body="Body",
    )
    post.publish()
    return post


class TestBrowseCommunityFeed:
    async def test_raises_when_community_unknown(self) -> None:
        posts = FakeCommunityPostRepository()
        communities = FakeCommunityQueryPort()
        service = BrowseCommunityFeedService(
            post_repository=posts, community_query_port=communities
        )

        with pytest.raises(CommunityNotFoundForPostError):
            await service.browse(BrowseCommunityFeedInput(community_id=uuid4()))

    async def test_returns_only_published_posts_in_the_community(self) -> None:
        posts = FakeCommunityPostRepository()
        communities = FakeCommunityQueryPort()
        community_id, org_id = uuid4(), uuid4()
        communities.add_community(
            make_community_summary(community_id=community_id, organization_id=org_id)
        )
        published = _make_published_post(community_id=community_id, organization_id=org_id)
        draft = CommunityPost.create(
            community_id=community_id,
            organization_id=org_id,
            author_id=uuid4(),
            title=PostTitle("Draft"),
            body="Body",
        )
        other_community = _make_published_post(community_id=uuid4(), organization_id=org_id)
        await posts.add(published)
        await posts.add(draft)
        await posts.add(other_community)
        service = BrowseCommunityFeedService(
            post_repository=posts, community_query_port=communities
        )

        result = await service.browse(BrowseCommunityFeedInput(community_id=community_id))
        assert [item.post_id for item in result.items] == [published.id]

    async def test_pinned_posts_are_surfaced_first_on_page_one(self) -> None:
        posts = FakeCommunityPostRepository()
        communities = FakeCommunityQueryPort()
        community_id, org_id = uuid4(), uuid4()
        communities.add_community(
            make_community_summary(community_id=community_id, organization_id=org_id)
        )
        regular = _make_published_post(community_id=community_id, organization_id=org_id)
        pinned = _make_published_post(community_id=community_id, organization_id=org_id)
        pinned.set_pinned(True)
        await posts.add(regular)
        await posts.add(pinned)
        service = BrowseCommunityFeedService(
            post_repository=posts, community_query_port=communities
        )

        result = await service.browse(BrowseCommunityFeedInput(community_id=community_id))
        assert result.items[0].post_id == pinned.id

    async def test_pinned_post_not_reinjected_on_second_page(self) -> None:
        posts = FakeCommunityPostRepository()
        communities = FakeCommunityQueryPort()
        community_id, org_id = uuid4(), uuid4()
        communities.add_community(
            make_community_summary(community_id=community_id, organization_id=org_id)
        )
        pinned = _make_published_post(community_id=community_id, organization_id=org_id)
        pinned.set_pinned(True)
        regular_posts = [
            _make_published_post(community_id=community_id, organization_id=org_id)
            for _ in range(2)
        ]
        await posts.add(pinned)
        for post in regular_posts:
            await posts.add(post)
        service = BrowseCommunityFeedService(
            post_repository=posts, community_query_port=communities
        )

        first_page = await service.browse(
            BrowseCommunityFeedInput(community_id=community_id, limit=2)
        )
        assert first_page.next_cursor is not None

        second_page = await service.browse(
            BrowseCommunityFeedInput(
                community_id=community_id, cursor=first_page.next_cursor, limit=2
            )
        )
        assert pinned.id not in [item.post_id for item in second_page.items]

    async def test_cursor_pagination_covers_all_posts_without_duplicates(self) -> None:
        posts = FakeCommunityPostRepository()
        communities = FakeCommunityQueryPort()
        community_id, org_id = uuid4(), uuid4()
        communities.add_community(
            make_community_summary(community_id=community_id, organization_id=org_id)
        )
        created = [
            _make_published_post(community_id=community_id, organization_id=org_id)
            for _ in range(5)
        ]
        for post in created:
            await posts.add(post)
        service = BrowseCommunityFeedService(
            post_repository=posts, community_query_port=communities
        )

        seen: list[object] = []
        cursor: str | None = None
        for _ in range(10):
            page = await service.browse(
                BrowseCommunityFeedInput(community_id=community_id, cursor=cursor, limit=2)
            )
            seen.extend(item.post_id for item in page.items)
            cursor = page.next_cursor
            if cursor is None:
                break

        assert sorted(seen, key=str) == sorted((p.id for p in created), key=str)
        assert len(seen) == len(set(seen))
