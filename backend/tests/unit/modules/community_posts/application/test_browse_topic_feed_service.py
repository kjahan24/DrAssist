"""Unit tests for `BrowseTopicFeedService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community_posts.application.dto import BrowseTopicFeedInput
from app.modules.community_posts.application.services.browse_topic_feed_service import (
    BrowseTopicFeedService,
)
from app.modules.community_posts.domain.entities import CommunityPost
from app.modules.community_posts.domain.exceptions import TopicNotFoundForPostError
from app.modules.community_posts.domain.value_objects import PostTitle
from tests.unit.modules.community_posts.application.fakes import (
    FakeCommunityPostRepository,
    FakeTopicQueryPort,
)


def _make_published_post(*, organization_id: object) -> CommunityPost:
    post = CommunityPost.create(
        community_id=uuid4(),
        organization_id=organization_id,  # type: ignore[arg-type]
        author_id=uuid4(),
        title=PostTitle("Title"),
        body="Body",
    )
    post.publish()
    return post


class TestBrowseTopicFeed:
    async def test_raises_when_topic_unknown(self) -> None:
        posts = FakeCommunityPostRepository()
        topics = FakeTopicQueryPort()
        service = BrowseTopicFeedService(post_repository=posts, topic_query_port=topics)

        with pytest.raises(TopicNotFoundForPostError):
            await service.browse(BrowseTopicFeedInput(organization_id=uuid4(), topic_id=uuid4()))

    async def test_returns_only_posts_assigned_to_the_topic(self) -> None:
        posts = FakeCommunityPostRepository()
        topics = FakeTopicQueryPort()
        org_id, topic_id = uuid4(), uuid4()
        topics.add_topic(topic_id)
        matching = _make_published_post(organization_id=org_id)
        posts.assign_topic_for_search(matching.id, topic_id)
        unassigned = _make_published_post(organization_id=org_id)
        await posts.add(matching)
        await posts.add(unassigned)
        service = BrowseTopicFeedService(post_repository=posts, topic_query_port=topics)

        result = await service.browse(
            BrowseTopicFeedInput(organization_id=org_id, topic_id=topic_id)
        )
        assert [item.post_id for item in result.items] == [matching.id]

    async def test_excludes_unpublished_posts(self) -> None:
        posts = FakeCommunityPostRepository()
        topics = FakeTopicQueryPort()
        org_id, topic_id = uuid4(), uuid4()
        topics.add_topic(topic_id)
        published = _make_published_post(organization_id=org_id)
        posts.assign_topic_for_search(published.id, topic_id)
        draft = CommunityPost.create(
            community_id=uuid4(),
            organization_id=org_id,
            author_id=uuid4(),
            title=PostTitle("Draft"),
            body="Body",
        )
        posts.assign_topic_for_search(draft.id, topic_id)
        await posts.add(published)
        await posts.add(draft)
        service = BrowseTopicFeedService(post_repository=posts, topic_query_port=topics)

        result = await service.browse(
            BrowseTopicFeedInput(organization_id=org_id, topic_id=topic_id)
        )
        assert [item.post_id for item in result.items] == [published.id]

    async def test_empty_feed_returns_no_items_and_no_cursor(self) -> None:
        posts = FakeCommunityPostRepository()
        topics = FakeTopicQueryPort()
        org_id, topic_id = uuid4(), uuid4()
        topics.add_topic(topic_id)
        service = BrowseTopicFeedService(post_repository=posts, topic_query_port=topics)

        result = await service.browse(
            BrowseTopicFeedInput(organization_id=org_id, topic_id=topic_id)
        )
        assert result.items == ()
        assert result.next_cursor is None

    async def test_cursor_pagination_covers_all_posts_without_duplicates(self) -> None:
        posts = FakeCommunityPostRepository()
        topics = FakeTopicQueryPort()
        org_id, topic_id = uuid4(), uuid4()
        topics.add_topic(topic_id)
        created = [_make_published_post(organization_id=org_id) for _ in range(5)]
        for post in created:
            posts.assign_topic_for_search(post.id, topic_id)
            await posts.add(post)
        service = BrowseTopicFeedService(post_repository=posts, topic_query_port=topics)

        seen: list[object] = []
        cursor: str | None = None
        for _ in range(10):
            page = await service.browse(
                BrowseTopicFeedInput(
                    organization_id=org_id, topic_id=topic_id, cursor=cursor, limit=2
                )
            )
            seen.extend(item.post_id for item in page.items)
            cursor = page.next_cursor
            if cursor is None:
                break

        assert sorted(seen, key=str) == sorted((p.id for p in created), key=str)
        assert len(seen) == len(set(seen))

    async def test_scopes_to_organization(self) -> None:
        posts = FakeCommunityPostRepository()
        topics = FakeTopicQueryPort()
        org_id, topic_id = uuid4(), uuid4()
        topics.add_topic(topic_id)
        matching = _make_published_post(organization_id=org_id)
        posts.assign_topic_for_search(matching.id, topic_id)
        other_org = _make_published_post(organization_id=uuid4())
        posts.assign_topic_for_search(other_org.id, topic_id)
        await posts.add(matching)
        await posts.add(other_org)
        service = BrowseTopicFeedService(post_repository=posts, topic_query_port=topics)

        result = await service.browse(
            BrowseTopicFeedInput(organization_id=org_id, topic_id=topic_id)
        )
        assert [item.post_id for item in result.items] == [matching.id]
