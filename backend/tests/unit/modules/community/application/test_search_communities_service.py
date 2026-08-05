"""Unit tests for `SearchCommunitiesService`, using in-memory fakes."""

from uuid import uuid4

from app.modules.community.application.dto import SearchCommunitiesInput
from app.modules.community.application.services.search_communities_service import (
    SearchCommunitiesService,
)
from app.modules.community.domain.entities import Community
from app.modules.community.domain.value_objects import (
    CommunityDescription,
    CommunityName,
    CommunitySlug,
)
from tests.unit.modules.community.application.fakes import FakeCommunityRepository


def _seeded() -> tuple[SearchCommunitiesService, FakeCommunityRepository]:
    communities = FakeCommunityRepository()
    service = SearchCommunitiesService(community_repository=communities)
    return service, communities


class TestSearchCommunities:
    async def test_matches_by_name(self) -> None:
        service, communities = _seeded()
        organization_id = uuid4()
        oncology = Community.create(
            organization_id=organization_id,
            slug=CommunitySlug("oncology"),
            name=CommunityName("Oncology"),
        )
        await communities.add(oncology)
        cardiology = Community.create(
            organization_id=organization_id,
            slug=CommunitySlug("cardiology"),
            name=CommunityName("Cardiology"),
        )
        await communities.add(cardiology)

        output = await service.search(
            SearchCommunitiesInput(organization_id=organization_id, query="onco")
        )
        assert output.total == 1
        assert output.items[0].community_id == oncology.id

    async def test_matches_by_description(self) -> None:
        service, communities = _seeded()
        organization_id = uuid4()
        community = Community.create(
            organization_id=organization_id,
            slug=CommunitySlug("support-group"),
            name=CommunityName("Support Group"),
            description=CommunityDescription("A place to discuss diabetes management."),
        )
        await communities.add(community)

        output = await service.search(
            SearchCommunitiesInput(organization_id=organization_id, query="diabetes")
        )
        assert output.total == 1
        assert output.items[0].community_id == community.id

    async def test_no_matches_returns_empty(self) -> None:
        service, communities = _seeded()
        organization_id = uuid4()
        community = Community.create(
            organization_id=organization_id,
            slug=CommunitySlug("oncology"),
            name=CommunityName("Oncology"),
        )
        await communities.add(community)

        output = await service.search(
            SearchCommunitiesInput(organization_id=organization_id, query="nephrology")
        )
        assert output.total == 0
        assert output.items == ()

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
            slug=CommunitySlug("oncology-2"),
            name=CommunityName("Oncology Two"),
        )
        await communities.add(other)

        output = await service.search(
            SearchCommunitiesInput(
                organization_id=organization_id, query="oncology", category_id=category_id
            )
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
            slug=CommunitySlug("oncology-2"),
            name=CommunityName("Oncology Two"),
        )
        await communities.add(other)

        output = await service.search(
            SearchCommunitiesInput(
                organization_id=organization_id, query="oncology", tag_ids=(tag_id,)
            )
        )
        assert output.total == 1
        assert output.items[0].community_id == matching.id

    async def test_respects_offset_and_limit(self) -> None:
        service, communities = _seeded()
        organization_id = uuid4()
        for i in range(3):
            community = Community.create(
                organization_id=organization_id,
                slug=CommunitySlug(f"oncology-{i}"),
                name=CommunityName(f"Oncology {i}"),
            )
            await communities.add(community)

        output = await service.search(
            SearchCommunitiesInput(
                organization_id=organization_id, query="oncology", offset=1, limit=1
            )
        )
        assert len(output.items) == 1
        assert output.total == 3
