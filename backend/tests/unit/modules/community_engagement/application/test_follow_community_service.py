"""Unit tests for `FollowCommunityService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community_engagement.application.dto import FollowCommunityInput
from app.modules.community_engagement.application.services.follow_community_service import (
    FollowCommunityService,
)
from app.modules.community_engagement.domain.enums import FollowTargetType
from app.modules.community_engagement.domain.events import CommunityFollowed
from app.modules.community_engagement.domain.exceptions import CommunityNotFoundForFollowError
from tests.unit.modules.community_engagement.application.fakes import (
    FakeCommunityFollowerRepository,
    FakeCommunityQueryPort,
    FakeUnitOfWork,
    make_community_summary,
)


def _seeded() -> (
    tuple[
        FollowCommunityService,
        FakeCommunityFollowerRepository,
        FakeCommunityQueryPort,
        FakeUnitOfWork,
    ]
):
    followers = FakeCommunityFollowerRepository()
    communities = FakeCommunityQueryPort()
    uow = FakeUnitOfWork()
    service = FollowCommunityService(
        community_follower_repository=followers, community_query_port=communities, unit_of_work=uow
    )
    return service, followers, communities, uow


class TestFollowCommunity:
    async def test_creates_a_follow(self) -> None:
        service, followers, communities, _ = _seeded()
        community_id, user_id, org_id = uuid4(), uuid4(), uuid4()
        communities.add_community(
            make_community_summary(community_id=community_id, organization_id=org_id)
        )

        result = await service.execute(
            FollowCommunityInput(user_id=user_id, organization_id=org_id, community_id=community_id)
        )
        assert result.follow_target_type is FollowTargetType.COMMUNITY
        assert result.target_id == community_id
        stored = await followers.get_follow(user_id, community_id)
        assert stored is not None

    async def test_unknown_community_raises(self) -> None:
        service, _, _, _ = _seeded()
        with pytest.raises(CommunityNotFoundForFollowError):
            await service.execute(
                FollowCommunityInput(user_id=uuid4(), organization_id=uuid4(), community_id=uuid4())
            )

    async def test_cross_tenant_community_raises_not_found(self) -> None:
        service, _, communities, _ = _seeded()
        community_id = uuid4()
        communities.add_community(
            make_community_summary(community_id=community_id, organization_id=uuid4())
        )

        with pytest.raises(CommunityNotFoundForFollowError):
            await service.execute(
                FollowCommunityInput(
                    user_id=uuid4(), organization_id=uuid4(), community_id=community_id
                )
            )

    async def test_does_not_require_prior_membership(self) -> None:
        """ "Follow a community before joining it" — this task's own
        DOMAIN RULES never gate following behind membership; see
        `FollowCommunityService`'s own docstring."""
        service, _, communities, _ = _seeded()
        community_id, org_id = uuid4(), uuid4()
        communities.add_community(
            make_community_summary(community_id=community_id, organization_id=org_id)
        )

        result = await service.execute(
            FollowCommunityInput(user_id=uuid4(), organization_id=org_id, community_id=community_id)
        )
        assert result.target_id == community_id

    async def test_idempotent_when_already_following(self) -> None:
        service, followers, communities, uow = _seeded()
        community_id, user_id, org_id = uuid4(), uuid4(), uuid4()
        communities.add_community(
            make_community_summary(community_id=community_id, organization_id=org_id)
        )
        first = await service.execute(
            FollowCommunityInput(user_id=user_id, organization_id=org_id, community_id=community_id)
        )

        uow.committed = False
        second = await service.execute(
            FollowCommunityInput(user_id=user_id, organization_id=org_id, community_id=community_id)
        )
        assert second.follow_id == first.follow_id
        assert uow.committed is False

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, communities, uow = _seeded()
        community_id, org_id = uuid4(), uuid4()
        communities.add_community(
            make_community_summary(community_id=community_id, organization_id=org_id)
        )

        await service.execute(
            FollowCommunityInput(user_id=uuid4(), organization_id=org_id, community_id=community_id)
        )
        assert uow.committed is True

    async def test_publishes_a_community_followed_event(self) -> None:
        service, _, communities, uow = _seeded()
        community_id, org_id = uuid4(), uuid4()
        communities.add_community(
            make_community_summary(community_id=community_id, organization_id=org_id)
        )

        await service.execute(
            FollowCommunityInput(user_id=uuid4(), organization_id=org_id, community_id=community_id)
        )
        assert any(isinstance(e, CommunityFollowed) for e in uow.published_events)
