"""Unit tests for `FeaturePostService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityRole
from app.modules.community_posts.application.dto import SetPostFeaturedInput
from app.modules.community_posts.application.services.feature_post_service import (
    FeaturePostService,
)
from app.modules.community_posts.domain.entities import CommunityPost
from app.modules.community_posts.domain.events import CommunityPostFeaturedChanged
from app.modules.community_posts.domain.exceptions import (
    InsufficientPostRoleError,
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
    tuple[FeaturePostService, FakeCommunityPostRepository, FakeCommunityQueryPort, FakeUnitOfWork]
):
    posts = FakeCommunityPostRepository()
    communities = FakeCommunityQueryPort()
    uow = FakeUnitOfWork()
    service = FeaturePostService(
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


class TestFeaturePost:
    async def test_moderator_features_the_post(self) -> None:
        service, posts, communities, _ = _seeded()
        post = await _seed_post(posts, communities)
        moderator_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=post.community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )

        await service.execute(
            SetPostFeaturedInput(post_id=post.id, acting_user_id=moderator_id, featured=True)
        )
        stored = await posts.get_by_id(post.id)
        assert stored is not None
        assert stored.is_featured is True

    async def test_author_cannot_feature_their_own_post(self) -> None:
        service, posts, communities, _ = _seeded()
        post = await _seed_post(posts, communities)
        communities.add_membership(
            make_member_summary(
                community_id=post.community_id, user_id=post.author_id, role=CommunityRole.MEMBER
            )
        )

        with pytest.raises(InsufficientPostRoleError):
            await service.execute(
                SetPostFeaturedInput(post_id=post.id, acting_user_id=post.author_id, featured=True)
            )

    async def test_unknown_post_raises(self) -> None:
        service, _, _, _ = _seeded()
        with pytest.raises(PostNotFoundError):
            await service.execute(
                SetPostFeaturedInput(post_id=uuid4(), acting_user_id=uuid4(), featured=True)
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, posts, communities, uow = _seeded()
        post = await _seed_post(posts, communities)
        moderator_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=post.community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )

        await service.execute(
            SetPostFeaturedInput(post_id=post.id, acting_user_id=moderator_id, featured=True)
        )
        assert uow.committed is True

    async def test_publishes_a_community_post_featured_changed_event(self) -> None:
        service, posts, communities, uow = _seeded()
        post = await _seed_post(posts, communities)
        moderator_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=post.community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )

        await service.execute(
            SetPostFeaturedInput(post_id=post.id, acting_user_id=moderator_id, featured=True)
        )
        assert any(isinstance(e, CommunityPostFeaturedChanged) for e in uow.published_events)
