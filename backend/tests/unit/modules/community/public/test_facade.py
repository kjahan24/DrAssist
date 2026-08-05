"""Unit tests for `CommunityFacade` — exercised through
`CommunityQueryPort` exactly as a future consumer module (Posts,
Questions, ...) would call it, per
`docs/backend-architecture/12_testing_architecture.md`'s "Contract
tests" framing."""

from uuid import uuid4

from app.modules.community.application.services.community_query_service import (
    CommunityMembershipQueryService,
    GetCommunityService,
)
from app.modules.community.domain.entities import Community, CommunityMember
from app.modules.community.domain.enums import CommunityRole
from app.modules.community.domain.value_objects import CommunityId, CommunityName, CommunitySlug
from app.modules.community.public.facade import CommunityFacade
from app.modules.community.public.interfaces import CommunityQueryPort
from tests.unit.modules.community.application.fakes import (
    FakeCommunityMemberRepository,
    FakeCommunityRepository,
)


def _facade() -> tuple[CommunityFacade, FakeCommunityRepository, FakeCommunityMemberRepository]:
    communities = FakeCommunityRepository()
    members = FakeCommunityMemberRepository()
    facade = CommunityFacade(
        query_service=GetCommunityService(community_repository=communities),
        membership_query_service=CommunityMembershipQueryService(
            community_member_repository=members
        ),
    )
    return facade, communities, members


class TestCommunityFacade:
    def test_is_a_community_query_port(self) -> None:
        facade, _, _ = _facade()
        assert isinstance(facade, CommunityQueryPort)

    async def test_community_exists_true_when_present(self) -> None:
        facade, communities, _ = _facade()
        community = Community.create(
            organization_id=uuid4(), slug=CommunitySlug("oncology"), name=CommunityName("Oncology")
        )
        await communities.add(community)

        assert await facade.community_exists(community.id) is True

    async def test_community_exists_false_when_absent(self) -> None:
        facade, _, _ = _facade()
        assert await facade.community_exists(uuid4()) is False

    async def test_get_community_summary_delegates_to_the_query_service(self) -> None:
        facade, communities, _ = _facade()
        community = Community.create(
            organization_id=uuid4(), slug=CommunitySlug("oncology"), name=CommunityName("Oncology")
        )
        await communities.add(community)

        summary = await facade.get_community_summary(community.id)

        assert summary is not None
        assert summary.community_id == community.id

    async def test_get_membership_delegates_to_the_membership_query_service(self) -> None:
        facade, _, members = _facade()
        community_id = uuid4()
        user_id = uuid4()
        member = CommunityMember.create(
            community_id=CommunityId(community_id), user_id=user_id, role=CommunityRole.ADMIN
        )
        await members.add(member)

        summary = await facade.get_membership(community_id, user_id)

        assert summary is not None
        assert summary.role is CommunityRole.ADMIN

    async def test_is_active_member_true_for_an_active_member(self) -> None:
        facade, _, members = _facade()
        community_id = uuid4()
        user_id = uuid4()
        await members.add(
            CommunityMember.create(community_id=CommunityId(community_id), user_id=user_id)
        )

        assert await facade.is_active_member(community_id, user_id) is True

    async def test_is_active_member_false_for_a_non_member(self) -> None:
        facade, _, _ = _facade()
        assert await facade.is_active_member(uuid4(), uuid4()) is False
