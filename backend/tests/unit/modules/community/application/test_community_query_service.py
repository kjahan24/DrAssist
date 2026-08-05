"""Unit tests for `GetCommunityService`, `ListCommunitiesService`, and
`CommunityMembershipQueryService`, using in-memory fakes."""

from uuid import uuid4

from app.modules.community.application.services.community_query_service import (
    CommunityMembershipQueryService,
    GetCommunityService,
    ListCommunitiesService,
)
from app.modules.community.domain.entities import Community, CommunityMember
from app.modules.community.domain.enums import CommunityRole, CommunityVisibility
from app.modules.community.domain.value_objects import (
    CommunityDescription,
    CommunityId,
    CommunityName,
    CommunitySlug,
)
from tests.unit.modules.community.application.fakes import (
    FakeCommunityMemberRepository,
    FakeCommunityRepository,
)


class TestGetCommunityService:
    async def test_get_by_id_returns_a_summary(self) -> None:
        communities = FakeCommunityRepository()
        service = GetCommunityService(community_repository=communities)
        community = Community.create(
            organization_id=uuid4(), slug=CommunitySlug("oncology"), name=CommunityName("Oncology")
        )
        await communities.add(community)

        summary = await service.get_by_id(community.id)

        assert summary is not None
        assert summary.community_id == community.id
        assert summary.slug == "oncology"
        assert summary.name == "Oncology"
        assert summary.id == community.id  # alias property

    async def test_get_by_id_returns_none_for_unknown_id(self) -> None:
        service = GetCommunityService(community_repository=FakeCommunityRepository())
        assert await service.get_by_id(uuid4()) is None

    async def test_get_by_slug_returns_a_summary(self) -> None:
        communities = FakeCommunityRepository()
        service = GetCommunityService(community_repository=communities)
        organization_id = uuid4()
        community = Community.create(
            organization_id=organization_id,
            slug=CommunitySlug("oncology"),
            name=CommunityName("Oncology"),
        )
        await communities.add(community)

        summary = await service.get_by_slug(organization_id, "oncology")

        assert summary is not None
        assert summary.community_id == community.id

    async def test_get_by_slug_is_organization_scoped(self) -> None:
        communities = FakeCommunityRepository()
        service = GetCommunityService(community_repository=communities)
        community = Community.create(
            organization_id=uuid4(), slug=CommunitySlug("oncology"), name=CommunityName("Oncology")
        )
        await communities.add(community)

        summary = await service.get_by_slug(uuid4(), "oncology")

        assert summary is None

    async def test_get_by_slug_returns_none_for_unknown_slug(self) -> None:
        service = GetCommunityService(community_repository=FakeCommunityRepository())
        assert await service.get_by_slug(uuid4(), "unknown") is None

    async def test_summary_includes_description_when_present(self) -> None:
        communities = FakeCommunityRepository()
        service = GetCommunityService(community_repository=communities)
        community = Community.create(
            organization_id=uuid4(),
            slug=CommunitySlug("oncology"),
            name=CommunityName("Oncology"),
            description=CommunityDescription("A group."),
        )
        await communities.add(community)

        summary = await service.get_by_id(community.id)

        assert summary is not None
        assert summary.description == "A group."


class TestListCommunitiesService:
    async def test_lists_communities_for_the_organization(self) -> None:
        communities = FakeCommunityRepository()
        service = ListCommunitiesService(community_repository=communities)
        organization_id = uuid4()
        community = Community.create(
            organization_id=organization_id,
            slug=CommunitySlug("oncology"),
            name=CommunityName("Oncology"),
        )
        await communities.add(community)

        result = await service.list_communities(organization_id=organization_id)

        assert result.total == 1
        assert result.items[0].community_id == community.id

    async def test_excludes_other_organizations(self) -> None:
        communities = FakeCommunityRepository()
        service = ListCommunitiesService(community_repository=communities)
        await communities.add(
            Community.create(
                organization_id=uuid4(),
                slug=CommunitySlug("oncology"),
                name=CommunityName("Oncology"),
            )
        )

        result = await service.list_communities(organization_id=uuid4())

        assert result.total == 0
        assert result.items == ()

    async def test_filters_by_visibility(self) -> None:
        communities = FakeCommunityRepository()
        service = ListCommunitiesService(community_repository=communities)
        organization_id = uuid4()
        public_community = Community.create(
            organization_id=organization_id,
            slug=CommunitySlug("public-group"),
            name=CommunityName("Public Group"),
            visibility=CommunityVisibility.PUBLIC,
        )
        private_community = Community.create(
            organization_id=organization_id,
            slug=CommunitySlug("private-group"),
            name=CommunityName("Private Group"),
            visibility=CommunityVisibility.PRIVATE,
        )
        await communities.add(public_community)
        await communities.add(private_community)

        result = await service.list_communities(
            organization_id=organization_id, visibilities=[CommunityVisibility.PRIVATE]
        )

        assert result.total == 1
        assert result.items[0].community_id == private_community.id

    async def test_query_filters_by_name(self) -> None:
        communities = FakeCommunityRepository()
        service = ListCommunitiesService(community_repository=communities)
        organization_id = uuid4()
        await communities.add(
            Community.create(
                organization_id=organization_id,
                slug=CommunitySlug("oncology"),
                name=CommunityName("Oncology"),
            )
        )
        await communities.add(
            Community.create(
                organization_id=organization_id,
                slug=CommunitySlug("cardiology"),
                name=CommunityName("Cardiology"),
            )
        )

        result = await service.list_communities(organization_id=organization_id, query="onco")

        assert result.total == 1
        assert result.items[0].slug == "oncology"

    async def test_respects_pagination(self) -> None:
        communities = FakeCommunityRepository()
        service = ListCommunitiesService(community_repository=communities)
        organization_id = uuid4()
        for index in range(5):
            await communities.add(
                Community.create(
                    organization_id=organization_id,
                    slug=CommunitySlug(f"group-{index}"),
                    name=CommunityName(f"Group {index}"),
                )
            )

        result = await service.list_communities(organization_id=organization_id, offset=2, limit=2)

        assert result.total == 5

    async def test_sort_order_descending(self) -> None:
        communities = FakeCommunityRepository()
        service = ListCommunitiesService(community_repository=communities)
        organization_id = uuid4()
        await communities.add(
            Community.create(
                organization_id=organization_id,
                slug=CommunitySlug("alpha"),
                name=CommunityName("Alpha"),
            )
        )
        await communities.add(
            Community.create(
                organization_id=organization_id,
                slug=CommunitySlug("beta"),
                name=CommunityName("Beta"),
            )
        )

        result = await service.list_communities(
            organization_id=organization_id, sort_by="name", sort_order="desc"
        )

        assert [item.name for item in result.items] == ["Beta", "Alpha"]

    async def test_empty_organization_returns_empty_result(self) -> None:
        service = ListCommunitiesService(community_repository=FakeCommunityRepository())

        result = await service.list_communities(organization_id=uuid4())

        assert result.total == 0
        assert result.items == ()


class TestCommunityMembershipQueryService:
    async def test_get_membership_returns_a_summary(self) -> None:
        members = FakeCommunityMemberRepository()
        service = CommunityMembershipQueryService(community_member_repository=members)
        community_id = uuid4()
        user_id = uuid4()
        member = CommunityMember.create(
            community_id=CommunityId(community_id), user_id=user_id, role=CommunityRole.MODERATOR
        )
        await members.add(member)

        summary = await service.get_membership(community_id, user_id)

        assert summary is not None
        assert summary.member_id == member.id
        assert summary.role is CommunityRole.MODERATOR
        assert summary.id == member.id  # alias property

    async def test_get_membership_returns_none_when_absent(self) -> None:
        service = CommunityMembershipQueryService(
            community_member_repository=FakeCommunityMemberRepository()
        )
        assert await service.get_membership(uuid4(), uuid4()) is None

    async def test_is_active_member_true_for_active_membership(self) -> None:
        members = FakeCommunityMemberRepository()
        service = CommunityMembershipQueryService(community_member_repository=members)
        community_id = uuid4()
        user_id = uuid4()
        await members.add(
            CommunityMember.create(community_id=CommunityId(community_id), user_id=user_id)
        )

        assert await service.is_active_member(community_id, user_id) is True

    async def test_is_active_member_false_for_left_membership(self) -> None:
        members = FakeCommunityMemberRepository()
        service = CommunityMembershipQueryService(community_member_repository=members)
        community_id = uuid4()
        user_id = uuid4()
        member = CommunityMember.create(community_id=CommunityId(community_id), user_id=user_id)
        member.leave()
        await members.add(member)

        assert await service.is_active_member(community_id, user_id) is False

    async def test_is_active_member_false_when_no_membership_exists(self) -> None:
        service = CommunityMembershipQueryService(
            community_member_repository=FakeCommunityMemberRepository()
        )
        assert await service.is_active_member(uuid4(), uuid4()) is False
