"""Unit tests for `DeleteCommunityService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.application.dto import DeleteCommunityInput
from app.modules.community.application.services.delete_community_service import (
    DeleteCommunityService,
)
from app.modules.community.domain.entities import Community, CommunityMember
from app.modules.community.domain.enums import CommunityRole
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
    DeleteCommunityService, FakeCommunityRepository, Community, CommunityMember, FakeUnitOfWork
]:
    communities = FakeCommunityRepository()
    members = FakeCommunityMemberRepository()
    uow = FakeUnitOfWork()
    service = DeleteCommunityService(
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


class TestDeleteCommunity:
    async def test_removes_the_community(self) -> None:
        service, communities, community, member, _ = await _seeded()
        await service.execute(
            DeleteCommunityInput(community_id=community.id, acting_user_id=member.user_id)
        )
        assert await communities.get_by_id(community.id) is None

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, community, member, uow = await _seeded()
        await service.execute(
            DeleteCommunityInput(community_id=community.id, acting_user_id=member.user_id)
        )
        assert uow.committed is True

    async def test_unknown_community_raises(self) -> None:
        service, _, _, member, _ = await _seeded()
        with pytest.raises(CommunityNotFoundError):
            await service.execute(
                DeleteCommunityInput(community_id=uuid4(), acting_user_id=member.user_id)
            )

    async def test_acting_user_with_no_membership_raises(self) -> None:
        service, _, community, _, _ = await _seeded()
        with pytest.raises(CommunityMembershipNotFoundError):
            await service.execute(
                DeleteCommunityInput(community_id=community.id, acting_user_id=uuid4())
            )

    async def test_member_role_is_insufficient(self) -> None:
        service, _, community, member, _ = await _seeded(role=CommunityRole.MEMBER)
        with pytest.raises(InsufficientCommunityRoleError):
            await service.execute(
                DeleteCommunityInput(community_id=community.id, acting_user_id=member.user_id)
            )

    async def test_admin_role_is_insufficient(self) -> None:
        """Deletion requires `OWNER`, unlike `UpdateCommunityService` which
        accepts `ADMIN` — see this service's own module docstring."""
        service, _, community, member, _ = await _seeded(role=CommunityRole.ADMIN)
        with pytest.raises(InsufficientCommunityRoleError):
            await service.execute(
                DeleteCommunityInput(community_id=community.id, acting_user_id=member.user_id)
            )

    async def test_owner_role_is_sufficient(self) -> None:
        service, communities, community, member, _ = await _seeded(role=CommunityRole.OWNER)
        await service.execute(
            DeleteCommunityInput(community_id=community.id, acting_user_id=member.user_id)
        )
        assert await communities.get_by_id(community.id) is None
