"""Unit tests for `PublishPostService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityRole
from app.modules.community_posts.application.dto import PublishPostInput
from app.modules.community_posts.application.services.publish_post_service import (
    PublishPostService,
)
from app.modules.community_posts.domain.entities import CommunityPost
from app.modules.community_posts.domain.enums import PostStatus
from app.modules.community_posts.domain.events import CommunityPostPublished
from app.modules.community_posts.domain.exceptions import (
    InsufficientPostRoleError,
    PostAlreadyPublishedError,
    PostNotFoundError,
)
from app.modules.community_posts.domain.value_objects import PostTitle
from tests.unit.modules.community_posts.application.fakes import (
    FakeCommunityPostRepository,
    FakeCommunityQueryPort,
    FakeUnitOfWork,
    make_community_summary,
    make_member_summary,
)


def _seeded() -> (
    tuple[PublishPostService, FakeCommunityPostRepository, FakeCommunityQueryPort, FakeUnitOfWork]
):
    posts = FakeCommunityPostRepository()
    communities = FakeCommunityQueryPort()
    uow = FakeUnitOfWork()
    service = PublishPostService(
        post_repository=posts, community_query_port=communities, unit_of_work=uow
    )
    return service, posts, communities, uow


async def _seed_post(
    posts: FakeCommunityPostRepository, communities: FakeCommunityQueryPort
) -> CommunityPost:
    post = CommunityPost.create(
        community_id=uuid4(),
        organization_id=uuid4(),
        author_id=uuid4(),
        title=PostTitle("Title"),
        body="Body",
    )
    await posts.add(post)
    communities.add_community(make_community_summary(community_id=post.community_id))
    return post


class TestPublishPost:
    async def test_author_publishes_the_post(self) -> None:
        service, posts, communities, _ = _seeded()
        post = await _seed_post(posts, communities)

        await service.execute(PublishPostInput(post_id=post.id, acting_user_id=post.author_id))

        stored = await posts.get_by_id(post.id)
        assert stored is not None
        assert stored.status is PostStatus.PUBLISHED
        assert stored.published_at is not None

    async def test_moderator_can_publish_someone_elses_post(self) -> None:
        service, posts, communities, _ = _seeded()
        post = await _seed_post(posts, communities)
        moderator_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=post.community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )

        await service.execute(PublishPostInput(post_id=post.id, acting_user_id=moderator_id))
        stored = await posts.get_by_id(post.id)
        assert stored is not None
        assert stored.status is PostStatus.PUBLISHED

    async def test_plain_member_cannot_publish_someone_elses_post(self) -> None:
        service, posts, communities, _ = _seeded()
        post = await _seed_post(posts, communities)
        member_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=post.community_id, user_id=member_id, role=CommunityRole.MEMBER
            )
        )

        with pytest.raises(InsufficientPostRoleError):
            await service.execute(PublishPostInput(post_id=post.id, acting_user_id=member_id))

    async def test_unknown_post_raises(self) -> None:
        service, _, _, _ = _seeded()
        with pytest.raises(PostNotFoundError):
            await service.execute(PublishPostInput(post_id=uuid4(), acting_user_id=uuid4()))

    async def test_already_published_raises(self) -> None:
        service, posts, communities, _ = _seeded()
        post = await _seed_post(posts, communities)
        await service.execute(PublishPostInput(post_id=post.id, acting_user_id=post.author_id))

        with pytest.raises(PostAlreadyPublishedError):
            await service.execute(PublishPostInput(post_id=post.id, acting_user_id=post.author_id))

    async def test_commits_the_unit_of_work(self) -> None:
        service, posts, communities, uow = _seeded()
        post = await _seed_post(posts, communities)
        await service.execute(PublishPostInput(post_id=post.id, acting_user_id=post.author_id))
        assert uow.committed is True

    async def test_publishes_a_community_post_published_event(self) -> None:
        service, posts, communities, uow = _seeded()
        post = await _seed_post(posts, communities)
        await service.execute(PublishPostInput(post_id=post.id, acting_user_id=post.author_id))
        assert any(isinstance(e, CommunityPostPublished) for e in uow.published_events)

    async def test_returns_a_summary_with_published_status(self) -> None:
        service, posts, communities, _ = _seeded()
        post = await _seed_post(posts, communities)
        summary = await service.execute(
            PublishPostInput(post_id=post.id, acting_user_id=post.author_id)
        )
        assert summary.status is PostStatus.PUBLISHED
