"""Unit tests for `FeatureCommunitiesService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.application.dto import (
    ListFeaturedCommunitiesInput,
    SetCommunityFeaturedInput,
    SetCommunityVerifiedInput,
)
from app.modules.community.application.services.feature_communities_service import (
    FeatureCommunitiesService,
)
from app.modules.community.domain.entities import Community
from app.modules.community.domain.events import CommunityFeaturedChanged, CommunityVerifiedChanged
from app.modules.community.domain.exceptions import CommunityNotFoundError
from app.modules.community.domain.value_objects import CommunityName, CommunitySlug
from tests.unit.modules.community.application.fakes import FakeCommunityRepository, FakeUnitOfWork


def _seeded() -> tuple[FeatureCommunitiesService, FakeCommunityRepository, FakeUnitOfWork]:
    communities = FakeCommunityRepository()
    uow = FakeUnitOfWork()
    service = FeatureCommunitiesService(community_repository=communities, unit_of_work=uow)
    return service, communities, uow


class TestListFeatured:
    async def test_returns_only_featured_communities(self) -> None:
        service, communities, _ = _seeded()
        organization_id = uuid4()
        featured = Community.create(
            organization_id=organization_id,
            slug=CommunitySlug("oncology"),
            name=CommunityName("Oncology"),
        )
        featured.set_featured(True)
        await communities.add(featured)
        unfeatured = Community.create(
            organization_id=organization_id,
            slug=CommunitySlug("cardiology"),
            name=CommunityName("Cardiology"),
        )
        await communities.add(unfeatured)

        output = await service.list_featured(
            ListFeaturedCommunitiesInput(organization_id=organization_id)
        )
        assert output.total == 1
        assert output.items[0].community_id == featured.id

    async def test_no_featured_communities_returns_empty(self) -> None:
        service, communities, _ = _seeded()
        organization_id = uuid4()
        community = Community.create(
            organization_id=organization_id,
            slug=CommunitySlug("oncology"),
            name=CommunityName("Oncology"),
        )
        await communities.add(community)

        output = await service.list_featured(
            ListFeaturedCommunitiesInput(organization_id=organization_id)
        )
        assert output.total == 0


class TestSetFeatured:
    async def test_sets_a_community_as_featured(self) -> None:
        service, communities, _ = _seeded()
        community = Community.create(
            organization_id=uuid4(), slug=CommunitySlug("oncology"), name=CommunityName("Oncology")
        )
        await communities.add(community)

        await service.set_featured(
            SetCommunityFeaturedInput(community_id=community.id, featured=True)
        )

        stored = await communities.get_by_id(community.id)
        assert stored is not None
        assert stored.is_featured is True

    async def test_unsets_a_featured_community(self) -> None:
        service, communities, _ = _seeded()
        community = Community.create(
            organization_id=uuid4(), slug=CommunitySlug("oncology"), name=CommunityName("Oncology")
        )
        community.set_featured(True)
        await communities.add(community)

        await service.set_featured(
            SetCommunityFeaturedInput(community_id=community.id, featured=False)
        )

        stored = await communities.get_by_id(community.id)
        assert stored is not None
        assert stored.is_featured is False

    async def test_unknown_community_raises(self) -> None:
        service, _, _ = _seeded()
        with pytest.raises(CommunityNotFoundError):
            await service.set_featured(
                SetCommunityFeaturedInput(community_id=uuid4(), featured=True)
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, communities, uow = _seeded()
        community = Community.create(
            organization_id=uuid4(), slug=CommunitySlug("oncology"), name=CommunityName("Oncology")
        )
        await communities.add(community)
        await service.set_featured(
            SetCommunityFeaturedInput(community_id=community.id, featured=True)
        )
        assert uow.committed is True

    async def test_publishes_a_community_featured_changed_event(self) -> None:
        service, communities, uow = _seeded()
        community = Community.create(
            organization_id=uuid4(), slug=CommunitySlug("oncology"), name=CommunityName("Oncology")
        )
        await communities.add(community)
        await service.set_featured(
            SetCommunityFeaturedInput(community_id=community.id, featured=True)
        )
        assert any(isinstance(e, CommunityFeaturedChanged) for e in uow.published_events)


class TestSetVerified:
    async def test_sets_a_community_as_verified(self) -> None:
        service, communities, _ = _seeded()
        community = Community.create(
            organization_id=uuid4(), slug=CommunitySlug("oncology"), name=CommunityName("Oncology")
        )
        await communities.add(community)

        await service.set_verified(
            SetCommunityVerifiedInput(community_id=community.id, verified=True)
        )

        stored = await communities.get_by_id(community.id)
        assert stored is not None
        assert stored.is_verified is True

    async def test_unsets_a_verified_community(self) -> None:
        service, communities, _ = _seeded()
        community = Community.create(
            organization_id=uuid4(), slug=CommunitySlug("oncology"), name=CommunityName("Oncology")
        )
        community.set_verified(True)
        await communities.add(community)

        await service.set_verified(
            SetCommunityVerifiedInput(community_id=community.id, verified=False)
        )

        stored = await communities.get_by_id(community.id)
        assert stored is not None
        assert stored.is_verified is False

    async def test_unknown_community_raises(self) -> None:
        service, _, _ = _seeded()
        with pytest.raises(CommunityNotFoundError):
            await service.set_verified(
                SetCommunityVerifiedInput(community_id=uuid4(), verified=True)
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, communities, uow = _seeded()
        community = Community.create(
            organization_id=uuid4(), slug=CommunitySlug("oncology"), name=CommunityName("Oncology")
        )
        await communities.add(community)
        await service.set_verified(
            SetCommunityVerifiedInput(community_id=community.id, verified=True)
        )
        assert uow.committed is True

    async def test_publishes_a_community_verified_changed_event(self) -> None:
        service, communities, uow = _seeded()
        community = Community.create(
            organization_id=uuid4(), slug=CommunitySlug("oncology"), name=CommunityName("Oncology")
        )
        await communities.add(community)
        await service.set_verified(
            SetCommunityVerifiedInput(community_id=community.id, verified=True)
        )
        assert any(isinstance(e, CommunityVerifiedChanged) for e in uow.published_events)
