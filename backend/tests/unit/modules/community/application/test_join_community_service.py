"""Unit tests for `JoinCommunityService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.application.dto import JoinCommunityInput
from app.modules.community.application.services.join_community_service import JoinCommunityService
from app.modules.community.domain.entities import Community, CommunityMember
from app.modules.community.domain.enums import (
    CommunityMemberStatus,
    CommunityRole,
    CommunityVisibility,
)
from app.modules.community.domain.events import CommunityMemberJoined
from app.modules.community.domain.exceptions import (
    CommunityMemberBlockedError,
    CommunityMembershipAlreadyExistsError,
    CommunityNotFoundError,
    PrivateCommunityJoinRequiresInviteError,
)
from app.modules.community.domain.value_objects import CommunityId, CommunityName, CommunitySlug
from tests.unit.modules.community.application.fakes import (
    FakeCommunityMemberRepository,
    FakeCommunityRepository,
    FakeUnitOfWork,
)


def _build_service() -> (
    tuple[
        JoinCommunityService, FakeCommunityRepository, FakeCommunityMemberRepository, FakeUnitOfWork
    ]
):
    communities = FakeCommunityRepository()
    members = FakeCommunityMemberRepository()
    uow = FakeUnitOfWork()
    service = JoinCommunityService(
        community_repository=communities, community_member_repository=members, unit_of_work=uow
    )
    return service, communities, members, uow


async def _seed_community(
    communities: FakeCommunityRepository,
    *,
    visibility: CommunityVisibility = CommunityVisibility.PUBLIC,
) -> Community:
    community = Community.create(
        organization_id=uuid4(),
        slug=CommunitySlug("oncology"),
        name=CommunityName("Oncology"),
        visibility=visibility,
    )
    await communities.add(community)
    return community


class TestJoinCommunityFreshJoin:
    async def test_public_community_accepts_a_first_time_join(self) -> None:
        service, communities, members, _ = _build_service()
        community = await _seed_community(communities)
        user_id = uuid4()

        output = await service.execute(
            JoinCommunityInput(community_id=community.id, user_id=user_id)
        )

        assert output.status is CommunityMemberStatus.ACTIVE
        assert output.role is CommunityRole.MEMBER
        stored = await members.get_by_community_and_user(community.id, user_id)
        assert stored is not None

    async def test_verified_only_community_rejects_a_direct_join(self) -> None:
        service, communities, _, _ = _build_service()
        community = await _seed_community(communities, visibility=CommunityVisibility.VERIFIED_ONLY)

        with pytest.raises(PrivateCommunityJoinRequiresInviteError):
            await service.execute(JoinCommunityInput(community_id=community.id, user_id=uuid4()))

    async def test_private_community_rejects_a_direct_join(self) -> None:
        service, communities, _, _ = _build_service()
        community = await _seed_community(communities, visibility=CommunityVisibility.PRIVATE)

        with pytest.raises(PrivateCommunityJoinRequiresInviteError):
            await service.execute(JoinCommunityInput(community_id=community.id, user_id=uuid4()))

    async def test_unknown_community_raises(self) -> None:
        service, _, _, _ = _build_service()
        with pytest.raises(CommunityNotFoundError):
            await service.execute(JoinCommunityInput(community_id=uuid4(), user_id=uuid4()))

    async def test_commits_the_unit_of_work(self) -> None:
        service, communities, _, uow = _build_service()
        community = await _seed_community(communities)
        await service.execute(JoinCommunityInput(community_id=community.id, user_id=uuid4()))
        assert uow.committed is True

    async def test_publishes_a_member_joined_event(self) -> None:
        service, communities, _, uow = _build_service()
        community = await _seed_community(communities)
        await service.execute(JoinCommunityInput(community_id=community.id, user_id=uuid4()))
        assert any(isinstance(e, CommunityMemberJoined) for e in uow.published_events)


class TestJoinCommunityAlreadyActive:
    async def test_raises_membership_already_exists(self) -> None:
        service, communities, members, _ = _build_service()
        community = await _seed_community(communities)
        user_id = uuid4()
        existing = CommunityMember.create(community_id=CommunityId(community.id), user_id=user_id)
        await members.add(existing)

        with pytest.raises(CommunityMembershipAlreadyExistsError):
            await service.execute(JoinCommunityInput(community_id=community.id, user_id=user_id))


class TestJoinCommunityBlocked:
    async def test_raises_member_blocked(self) -> None:
        service, communities, members, _ = _build_service()
        community = await _seed_community(communities)
        user_id = uuid4()
        blocked = CommunityMember.create(
            community_id=CommunityId(community.id),
            user_id=user_id,
            status=CommunityMemberStatus.BLOCKED,
        )
        await members.add(blocked)

        with pytest.raises(CommunityMemberBlockedError):
            await service.execute(JoinCommunityInput(community_id=community.id, user_id=user_id))


class TestJoinCommunityRejoinAfterLeaving:
    async def test_public_community_allows_rejoining(self) -> None:
        service, communities, members, _ = _build_service()
        community = await _seed_community(communities)
        user_id = uuid4()
        left_member = CommunityMember.create(
            community_id=CommunityId(community.id), user_id=user_id
        )
        left_member.leave()
        await members.add(left_member)

        output = await service.execute(
            JoinCommunityInput(community_id=community.id, user_id=user_id)
        )

        assert output.status is CommunityMemberStatus.ACTIVE
        assert output.member_id == left_member.id

    async def test_private_community_rejects_rejoining_without_a_fresh_invite(self) -> None:
        service, communities, members, _ = _build_service()
        community = await _seed_community(communities, visibility=CommunityVisibility.PRIVATE)
        user_id = uuid4()
        left_member = CommunityMember.create(
            community_id=CommunityId(community.id), user_id=user_id
        )
        left_member.leave()
        await members.add(left_member)

        with pytest.raises(PrivateCommunityJoinRequiresInviteError):
            await service.execute(JoinCommunityInput(community_id=community.id, user_id=user_id))


class TestJoinCommunityAcceptingAnInvite:
    async def test_accepting_an_invite_to_a_private_community_succeeds(self) -> None:
        service, communities, members, _ = _build_service()
        community = await _seed_community(communities, visibility=CommunityVisibility.PRIVATE)
        user_id = uuid4()
        invited = CommunityMember.create(
            community_id=CommunityId(community.id),
            user_id=user_id,
            status=CommunityMemberStatus.INVITED,
        )
        await members.add(invited)

        output = await service.execute(
            JoinCommunityInput(community_id=community.id, user_id=user_id)
        )

        assert output.status is CommunityMemberStatus.ACTIVE
        assert output.member_id == invited.id

    async def test_accepting_an_invite_to_a_verified_only_community_succeeds(self) -> None:
        service, communities, members, _ = _build_service()
        community = await _seed_community(communities, visibility=CommunityVisibility.VERIFIED_ONLY)
        user_id = uuid4()
        invited = CommunityMember.create(
            community_id=CommunityId(community.id),
            user_id=user_id,
            status=CommunityMemberStatus.INVITED,
        )
        await members.add(invited)

        output = await service.execute(
            JoinCommunityInput(community_id=community.id, user_id=user_id)
        )

        assert output.status is CommunityMemberStatus.ACTIVE
