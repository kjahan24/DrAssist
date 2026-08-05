"""Unit tests for `UpdateCommunityService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.application.dto import UpdateCommunityInput
from app.modules.community.application.services.update_community_service import (
    UpdateCommunityService,
)
from app.modules.community.domain.entities import Community, CommunityMember
from app.modules.community.domain.enums import CommunityRole, CommunityVisibility
from app.modules.community.domain.events import CommunityUpdated
from app.modules.community.domain.exceptions import (
    CommunityMembershipNotFoundError,
    CommunityNotFoundError,
    InsufficientCommunityRoleError,
)
from app.modules.community.domain.value_objects import CommunityId, CommunityName, CommunitySlug
from tests.unit.modules.community.application.fakes import (
    FakeCommunityMemberRepository,
    FakeCommunityRepository,
    FakeUnitOfWork,
)


async def _seeded(
    role: CommunityRole = CommunityRole.OWNER,
) -> tuple[
    UpdateCommunityService, FakeCommunityRepository, Community, CommunityMember, FakeUnitOfWork
]:
    communities = FakeCommunityRepository()
    members = FakeCommunityMemberRepository()
    uow = FakeUnitOfWork()
    service = UpdateCommunityService(
        community_repository=communities, community_member_repository=members, unit_of_work=uow
    )

    community = Community.create(
        organization_id=uuid4(), slug=CommunitySlug("oncology"), name=CommunityName("Oncology")
    )
    await communities.add(community)

    acting_user_id = uuid4()
    member = CommunityMember.create(
        community_id=CommunityId(community.id), user_id=acting_user_id, role=role
    )
    await members.add(member)

    return service, communities, community, member, uow


class TestUpdateCommunity:
    async def test_updates_the_name(self) -> None:
        service, communities, community, member, _ = await _seeded()
        await service.execute(
            UpdateCommunityInput(
                community_id=community.id, acting_user_id=member.user_id, name="Renamed"
            )
        )
        stored = await communities.get_by_id(community.id)
        assert stored is not None
        assert str(stored.name) == "Renamed"

    async def test_updates_visibility(self) -> None:
        service, communities, community, member, _ = await _seeded()
        await service.execute(
            UpdateCommunityInput(
                community_id=community.id,
                acting_user_id=member.user_id,
                visibility=CommunityVisibility.PRIVATE,
            )
        )
        stored = await communities.get_by_id(community.id)
        assert stored is not None
        assert stored.visibility is CommunityVisibility.PRIVATE

    async def test_updates_description(self) -> None:
        service, communities, community, member, _ = await _seeded()
        await service.execute(
            UpdateCommunityInput(
                community_id=community.id,
                acting_user_id=member.user_id,
                description="Updated description.",
            )
        )
        stored = await communities.get_by_id(community.id)
        assert stored is not None
        assert str(stored.description) == "Updated description."

    async def test_clear_description_removes_it(self) -> None:
        service, communities, community, member, _ = await _seeded()
        await service.execute(
            UpdateCommunityInput(
                community_id=community.id, acting_user_id=member.user_id, description="Something"
            )
        )
        await service.execute(
            UpdateCommunityInput(
                community_id=community.id, acting_user_id=member.user_id, clear_description=True
            )
        )
        stored = await communities.get_by_id(community.id)
        assert stored is not None
        assert stored.description is None

    async def test_unknown_community_raises(self) -> None:
        service, _, _, member, _ = await _seeded()
        with pytest.raises(CommunityNotFoundError):
            await service.execute(
                UpdateCommunityInput(community_id=uuid4(), acting_user_id=member.user_id, name="X")
            )

    async def test_acting_user_with_no_membership_raises(self) -> None:
        service, _, community, _, _ = await _seeded()
        with pytest.raises(CommunityMembershipNotFoundError):
            await service.execute(
                UpdateCommunityInput(community_id=community.id, acting_user_id=uuid4(), name="X")
            )

    async def test_member_role_is_insufficient(self) -> None:
        service, _, community, member, _ = await _seeded(role=CommunityRole.MEMBER)
        with pytest.raises(InsufficientCommunityRoleError):
            await service.execute(
                UpdateCommunityInput(
                    community_id=community.id, acting_user_id=member.user_id, name="X"
                )
            )

    async def test_moderator_role_is_insufficient(self) -> None:
        service, _, community, member, _ = await _seeded(role=CommunityRole.MODERATOR)
        with pytest.raises(InsufficientCommunityRoleError):
            await service.execute(
                UpdateCommunityInput(
                    community_id=community.id, acting_user_id=member.user_id, name="X"
                )
            )

    async def test_admin_role_is_sufficient(self) -> None:
        service, communities, community, member, _ = await _seeded(role=CommunityRole.ADMIN)
        await service.execute(
            UpdateCommunityInput(
                community_id=community.id, acting_user_id=member.user_id, name="Renamed"
            )
        )
        stored = await communities.get_by_id(community.id)
        assert stored is not None
        assert str(stored.name) == "Renamed"

    async def test_owner_role_is_sufficient(self) -> None:
        service, communities, community, member, _ = await _seeded(role=CommunityRole.OWNER)
        await service.execute(
            UpdateCommunityInput(
                community_id=community.id, acting_user_id=member.user_id, name="Renamed"
            )
        )
        stored = await communities.get_by_id(community.id)
        assert stored is not None
        assert str(stored.name) == "Renamed"

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, community, member, uow = await _seeded()
        await service.execute(
            UpdateCommunityInput(community_id=community.id, acting_user_id=member.user_id, name="X")
        )
        assert uow.committed is True

    async def test_publishes_a_community_updated_event(self) -> None:
        service, _, community, member, uow = await _seeded()
        await service.execute(
            UpdateCommunityInput(community_id=community.id, acting_user_id=member.user_id, name="X")
        )
        assert any(isinstance(e, CommunityUpdated) for e in uow.published_events)

    async def test_output_reflects_the_update(self) -> None:
        service, _, community, member, _ = await _seeded()
        output = await service.execute(
            UpdateCommunityInput(
                community_id=community.id,
                acting_user_id=member.user_id,
                name="Renamed",
                visibility=CommunityVisibility.VERIFIED_ONLY,
            )
        )
        assert output.community_id == community.id
        assert output.name == "Renamed"
        assert output.visibility is CommunityVisibility.VERIFIED_ONLY
