"""Unit tests for `CreateCommunityService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.application.dto import CreateCommunityInput
from app.modules.community.application.services.create_community_service import (
    CreateCommunityService,
)
from app.modules.community.domain.enums import CommunityRole, CommunityVisibility
from app.modules.community.domain.events import CommunityCreated, CommunityMemberJoined
from app.modules.community.domain.exceptions import DuplicateCommunitySlugError
from tests.unit.modules.community.application.fakes import (
    FakeCommunityMemberRepository,
    FakeCommunityRepository,
    FakeUnitOfWork,
)


def _service() -> (
    tuple[
        CreateCommunityService,
        FakeCommunityRepository,
        FakeCommunityMemberRepository,
        FakeUnitOfWork,
    ]
):
    communities = FakeCommunityRepository()
    members = FakeCommunityMemberRepository()
    uow = FakeUnitOfWork()
    service = CreateCommunityService(
        community_repository=communities, community_member_repository=members, unit_of_work=uow
    )
    return service, communities, members, uow


class TestCreateCommunity:
    async def test_creates_a_community(self) -> None:
        service, communities, _, _ = _service()

        output = await service.execute(
            CreateCommunityInput(
                organization_id=uuid4(),
                slug="diabetes-support",
                name="Diabetes Support",
                created_by=uuid4(),
            )
        )

        stored = await communities.get_by_id(output.community_id)
        assert stored is not None
        assert str(stored.slug) == "diabetes-support"
        assert str(stored.name) == "Diabetes Support"

    async def test_creates_a_matching_owner_membership(self) -> None:
        service, _, members, _ = _service()
        organization_id = uuid4()
        creator_id = uuid4()

        output = await service.execute(
            CreateCommunityInput(
                organization_id=organization_id,
                slug="oncology",
                name="Oncology",
                created_by=creator_id,
            )
        )

        member = await members.get_by_community_and_user(output.community_id, creator_id)
        assert member is not None
        assert member.role is CommunityRole.OWNER

    async def test_defaults_to_public_visibility(self) -> None:
        service, communities, _, _ = _service()
        output = await service.execute(
            CreateCommunityInput(
                organization_id=uuid4(), slug="cardiology", name="Cardiology", created_by=uuid4()
            )
        )
        stored = await communities.get_by_id(output.community_id)
        assert stored is not None
        assert stored.visibility is CommunityVisibility.PUBLIC

    async def test_accepts_explicit_visibility(self) -> None:
        service, communities, _, _ = _service()
        output = await service.execute(
            CreateCommunityInput(
                organization_id=uuid4(),
                slug="private-group",
                name="Private Group",
                created_by=uuid4(),
                visibility=CommunityVisibility.PRIVATE,
            )
        )
        stored = await communities.get_by_id(output.community_id)
        assert stored is not None
        assert stored.visibility is CommunityVisibility.PRIVATE

    async def test_accepts_a_description(self) -> None:
        service, communities, _, _ = _service()
        output = await service.execute(
            CreateCommunityInput(
                organization_id=uuid4(),
                slug="neurology",
                name="Neurology",
                created_by=uuid4(),
                description="A group for neurology discussion.",
            )
        )
        stored = await communities.get_by_id(output.community_id)
        assert stored is not None
        assert str(stored.description) == "A group for neurology discussion."

    async def test_duplicate_slug_within_the_same_organization_is_rejected(self) -> None:
        service, _, _, _ = _service()
        organization_id = uuid4()

        await service.execute(
            CreateCommunityInput(
                organization_id=organization_id,
                slug="oncology",
                name="Oncology",
                created_by=uuid4(),
            )
        )

        with pytest.raises(DuplicateCommunitySlugError):
            await service.execute(
                CreateCommunityInput(
                    organization_id=organization_id,
                    slug="ONCOLOGY",
                    name="Oncology Two",
                    created_by=uuid4(),
                )
            )

    async def test_same_slug_in_different_organizations_is_allowed(self) -> None:
        service, communities, _, _ = _service()

        first = await service.execute(
            CreateCommunityInput(
                organization_id=uuid4(), slug="oncology", name="Oncology", created_by=uuid4()
            )
        )
        second = await service.execute(
            CreateCommunityInput(
                organization_id=uuid4(), slug="oncology", name="Oncology", created_by=uuid4()
            )
        )

        assert first.community_id != second.community_id
        assert await communities.get_by_id(first.community_id) is not None
        assert await communities.get_by_id(second.community_id) is not None

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, _, uow = _service()
        await service.execute(
            CreateCommunityInput(
                organization_id=uuid4(), slug="oncology", name="Oncology", created_by=uuid4()
            )
        )
        assert uow.committed is True

    async def test_publishes_community_created_and_member_joined_events(self) -> None:
        service, _, _, uow = _service()
        await service.execute(
            CreateCommunityInput(
                organization_id=uuid4(), slug="oncology", name="Oncology", created_by=uuid4()
            )
        )
        assert any(isinstance(e, CommunityCreated) for e in uow.published_events)
        assert any(isinstance(e, CommunityMemberJoined) for e in uow.published_events)

    async def test_output_reflects_the_created_community(self) -> None:
        service, _, _, _ = _service()
        organization_id = uuid4()
        output = await service.execute(
            CreateCommunityInput(
                organization_id=organization_id,
                slug="oncology",
                name="Oncology",
                created_by=uuid4(),
            )
        )
        assert output.organization_id == organization_id
        assert output.slug == "oncology"
        assert output.name == "Oncology"
        assert output.visibility is CommunityVisibility.PUBLIC
