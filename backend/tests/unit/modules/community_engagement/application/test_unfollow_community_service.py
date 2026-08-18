"""Unit tests for `UnfollowCommunityService` — unconditionally
idempotent."""

from uuid import uuid4

from app.modules.community_engagement.application.dto import UnfollowCommunityInput
from app.modules.community_engagement.application.services.unfollow_community_service import (
    UnfollowCommunityService,
)
from app.modules.community_engagement.domain.entities import CommunityFollower
from app.modules.community_engagement.domain.events import CommunityUnfollowed
from tests.unit.modules.community_engagement.application.fakes import (
    FakeCommunityFollowerRepository,
    FakeUnitOfWork,
)


def _seeded() -> tuple[UnfollowCommunityService, FakeCommunityFollowerRepository, FakeUnitOfWork]:
    followers = FakeCommunityFollowerRepository()
    uow = FakeUnitOfWork()
    service = UnfollowCommunityService(community_follower_repository=followers, unit_of_work=uow)
    return service, followers, uow


class TestUnfollowCommunity:
    async def test_removes_an_existing_follow(self) -> None:
        service, followers, _ = _seeded()
        user_id, community_id = uuid4(), uuid4()
        follower = CommunityFollower.create(
            user_id=user_id, organization_id=uuid4(), community_id=community_id
        )
        await followers.add(follower)

        await service.execute(UnfollowCommunityInput(user_id=user_id, community_id=community_id))
        assert await followers.get_follow(user_id, community_id) is None

    async def test_unfollowing_something_never_followed_is_a_silent_no_op(self) -> None:
        service, _, uow = _seeded()
        await service.execute(UnfollowCommunityInput(user_id=uuid4(), community_id=uuid4()))
        assert uow.committed is False

    async def test_commits_the_unit_of_work_when_a_follow_is_removed(self) -> None:
        service, followers, uow = _seeded()
        user_id, community_id = uuid4(), uuid4()
        follower = CommunityFollower.create(
            user_id=user_id, organization_id=uuid4(), community_id=community_id
        )
        await followers.add(follower)

        await service.execute(UnfollowCommunityInput(user_id=user_id, community_id=community_id))
        assert uow.committed is True

    async def test_publishes_a_community_unfollowed_event(self) -> None:
        service, followers, uow = _seeded()
        user_id, community_id = uuid4(), uuid4()
        follower = CommunityFollower.create(
            user_id=user_id, organization_id=uuid4(), community_id=community_id
        )
        await followers.add(follower)

        await service.execute(UnfollowCommunityInput(user_id=user_id, community_id=community_id))
        assert any(isinstance(e, CommunityUnfollowed) for e in uow.published_events)
