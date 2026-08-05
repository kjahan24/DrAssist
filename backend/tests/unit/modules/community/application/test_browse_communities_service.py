"""Unit tests for `BrowseCommunitiesService`, using in-memory fakes."""

from uuid import uuid4

from app.modules.community.application.dto import BrowseCommunitiesInput
from app.modules.community.application.services.browse_communities_service import (
    BrowseCommunitiesService,
)
from app.modules.community.domain.entities import Community
from app.modules.community.domain.enums import CommunityVisibility
from app.modules.community.domain.value_objects import CommunityName, CommunitySlug
from tests.unit.modules.community.application.fakes import FakeCommunityRepository


def _seeded() -> tuple[BrowseCommunitiesService, FakeCommunityRepository]:
    communities = FakeCommunityRepository()
    service = BrowseCommunitiesService(community_repository=communities)
    return service, communities


class TestBrowseCommunities:
    async def test_returns_communities_in_the_organization(self) -> None:
        service, communities = _seeded()
        organization_id = uuid4()
        community = Community.create(
            organization_id=organization_id,
            slug=CommunitySlug("oncology"),
            name=CommunityName("Oncology"),
        )
        await communities.add(community)

        output = await service.browse(BrowseCommunitiesInput(organization_id=organization_id))
        assert output.total == 1
        assert output.items[0].community_id == community.id

    async def test_excludes_communities_from_other_organizations(self) -> None:
        service, communities = _seeded()
        organization_id = uuid4()
        other = Community.create(
            organization_id=uuid4(), slug=CommunitySlug("oncology"), name=CommunityName("Oncology")
        )
        await communities.add(other)

        output = await service.browse(BrowseCommunitiesInput(organization_id=organization_id))
        assert output.total == 0

    async def test_filters_by_category_id(self) -> None:
        service, communities = _seeded()
        organization_id = uuid4()
        category_id = uuid4()
        matching = Community.create(
            organization_id=organization_id,
            slug=CommunitySlug("oncology"),
            name=CommunityName("Oncology"),
        )
        matching.update_profile(category_id=category_id)
        await communities.add(matching)
        other = Community.create(
            organization_id=organization_id,
            slug=CommunitySlug("cardiology"),
            name=CommunityName("Cardiology"),
        )
        await communities.add(other)

        output = await service.browse(
            BrowseCommunitiesInput(organization_id=organization_id, category_id=category_id)
        )
        assert output.total == 1
        assert output.items[0].community_id == matching.id

    async def test_filters_by_tag_ids(self) -> None:
        service, communities = _seeded()
        organization_id = uuid4()
        tag_id = uuid4()
        matching = Community.create(
            organization_id=organization_id,
            slug=CommunitySlug("oncology"),
            name=CommunityName("Oncology"),
        )
        await communities.add(matching)
        communities.add_tag_assignment(matching.id, tag_id)
        other = Community.create(
            organization_id=organization_id,
            slug=CommunitySlug("cardiology"),
            name=CommunityName("Cardiology"),
        )
        await communities.add(other)

        output = await service.browse(
            BrowseCommunitiesInput(organization_id=organization_id, tag_ids=(tag_id,))
        )
        assert output.total == 1
        assert output.items[0].community_id == matching.id

    async def test_filters_by_visibilities(self) -> None:
        service, communities = _seeded()
        organization_id = uuid4()
        public = Community.create(
            organization_id=organization_id,
            slug=CommunitySlug("oncology"),
            name=CommunityName("Oncology"),
            visibility=CommunityVisibility.PUBLIC,
        )
        await communities.add(public)
        private = Community.create(
            organization_id=organization_id,
            slug=CommunitySlug("cardiology"),
            name=CommunityName("Cardiology"),
            visibility=CommunityVisibility.PRIVATE,
        )
        await communities.add(private)

        output = await service.browse(
            BrowseCommunitiesInput(
                organization_id=organization_id, visibilities=(CommunityVisibility.PUBLIC,)
            )
        )
        assert output.total == 1
        assert output.items[0].community_id == public.id

    async def test_sort_alphabetical_orders_by_name_ascending(self) -> None:
        service, communities = _seeded()
        organization_id = uuid4()
        zebra = Community.create(
            organization_id=organization_id,
            slug=CommunitySlug("zebra"),
            name=CommunityName("Zebra"),
        )
        alpha = Community.create(
            organization_id=organization_id,
            slug=CommunitySlug("alpha"),
            name=CommunityName("Alpha"),
        )
        await communities.add(zebra)
        await communities.add(alpha)

        output = await service.browse(
            BrowseCommunitiesInput(organization_id=organization_id, sort="alphabetical")
        )
        assert [str(item.name) for item in output.items] == ["Alpha", "Zebra"]

    async def test_sort_popular_orders_by_member_count_descending(self) -> None:
        service, communities = _seeded()
        organization_id = uuid4()
        low = Community.create(
            organization_id=organization_id, slug=CommunitySlug("low"), name=CommunityName("Low")
        )
        high = Community.create(
            organization_id=organization_id, slug=CommunitySlug("high"), name=CommunityName("High")
        )
        await communities.add(low)
        await communities.add(high)
        communities.set_member_count(low.id, 2)
        communities.set_member_count(high.id, 50)

        output = await service.browse(
            BrowseCommunitiesInput(organization_id=organization_id, sort="popular")
        )
        assert [item.community_id for item in output.items] == [high.id, low.id]

    async def test_sort_recent_orders_by_created_at_descending(self) -> None:
        service, communities = _seeded()
        organization_id = uuid4()
        older = Community.create(
            organization_id=organization_id,
            slug=CommunitySlug("older"),
            name=CommunityName("Older"),
        )
        await communities.add(older)
        newer = Community.create(
            organization_id=organization_id,
            slug=CommunitySlug("newer"),
            name=CommunityName("Newer"),
        )
        newer.created_at = older.created_at.replace(year=older.created_at.year + 1)
        await communities.add(newer)

        output = await service.browse(
            BrowseCommunitiesInput(organization_id=organization_id, sort="recent")
        )
        assert output.items[0].community_id == newer.id

    async def test_respects_offset_and_limit(self) -> None:
        service, communities = _seeded()
        organization_id = uuid4()
        for i in range(3):
            community = Community.create(
                organization_id=organization_id,
                slug=CommunitySlug(f"community-{i}"),
                name=CommunityName(f"Community {i}"),
            )
            await communities.add(community)

        output = await service.browse(
            BrowseCommunitiesInput(organization_id=organization_id, offset=1, limit=1)
        )
        assert len(output.items) == 1
        assert output.total == 3
