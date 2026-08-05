"""Unit tests for `ManageCommunityTagsService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.application.dto import (
    AssignCommunityTagInput,
    SearchCommunityTagsInput,
    UnassignCommunityTagInput,
)
from app.modules.community.application.services.manage_community_tags_service import (
    ManageCommunityTagsService,
)
from app.modules.community.domain.entities import CommunityMember, CommunityTag
from app.modules.community.domain.enums import CommunityRole
from app.modules.community.domain.exceptions import (
    CommunityMembershipNotFoundError,
    CommunityTagAlreadyAssignedError,
    CommunityTagNotAssignedError,
    CommunityTagNotFoundError,
    InsufficientCommunityRoleError,
)
from app.modules.community.domain.value_objects import CommunityId, CommunityTagName
from tests.unit.modules.community.application.fakes import (
    FakeCommunityMemberRepository,
    FakeCommunityTagRepository,
    FakeUnitOfWork,
)


async def _seeded(
    role: CommunityRole = CommunityRole.ADMIN,
) -> tuple[
    ManageCommunityTagsService,
    FakeCommunityTagRepository,
    CommunityId,
    CommunityMember,
    FakeUnitOfWork,
]:
    tags = FakeCommunityTagRepository()
    members = FakeCommunityMemberRepository()
    uow = FakeUnitOfWork()
    service = ManageCommunityTagsService(
        community_tag_repository=tags, community_member_repository=members, unit_of_work=uow
    )

    community_id = CommunityId(uuid4())
    acting_user_id = uuid4()
    member = CommunityMember.create(community_id=community_id, user_id=acting_user_id, role=role)
    await members.add(member)

    return service, tags, community_id, member, uow


class TestAssignTag:
    async def test_assigns_a_new_tag_by_name(self) -> None:
        service, tags, community_id, member, _ = await _seeded()
        summary = await service.assign_tag(
            AssignCommunityTagInput(
                community_id=community_id.value, acting_user_id=member.user_id, tag_name="diabetes"
            )
        )
        assert summary.name == "diabetes"
        assert await tags.is_assigned(community_id.value, summary.tag_id) is True

    async def test_reuses_an_existing_tag_with_the_same_name(self) -> None:
        service, tags, community_id, member, _ = await _seeded()
        existing = CommunityTag.create(name=CommunityTagName("diabetes"))
        await tags.add(existing)

        summary = await service.assign_tag(
            AssignCommunityTagInput(
                community_id=community_id.value, acting_user_id=member.user_id, tag_name="Diabetes"
            )
        )
        assert summary.tag_id == existing.id

    async def test_assigning_an_already_assigned_tag_raises(self) -> None:
        service, _, community_id, member, _ = await _seeded()
        await service.assign_tag(
            AssignCommunityTagInput(
                community_id=community_id.value, acting_user_id=member.user_id, tag_name="diabetes"
            )
        )
        with pytest.raises(CommunityTagAlreadyAssignedError):
            await service.assign_tag(
                AssignCommunityTagInput(
                    community_id=community_id.value,
                    acting_user_id=member.user_id,
                    tag_name="diabetes",
                )
            )

    async def test_member_role_is_insufficient(self) -> None:
        service, _, community_id, member, _ = await _seeded(role=CommunityRole.MEMBER)
        with pytest.raises(InsufficientCommunityRoleError):
            await service.assign_tag(
                AssignCommunityTagInput(
                    community_id=community_id.value,
                    acting_user_id=member.user_id,
                    tag_name="diabetes",
                )
            )

    async def test_acting_user_with_no_membership_raises(self) -> None:
        service, _, community_id, _, _ = await _seeded()
        with pytest.raises(CommunityMembershipNotFoundError):
            await service.assign_tag(
                AssignCommunityTagInput(
                    community_id=community_id.value, acting_user_id=uuid4(), tag_name="diabetes"
                )
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, community_id, member, uow = await _seeded()
        await service.assign_tag(
            AssignCommunityTagInput(
                community_id=community_id.value, acting_user_id=member.user_id, tag_name="diabetes"
            )
        )
        assert uow.committed is True


class TestUnassignTag:
    async def test_removes_an_assigned_tag(self) -> None:
        service, tags, community_id, member, _ = await _seeded()
        summary = await service.assign_tag(
            AssignCommunityTagInput(
                community_id=community_id.value, acting_user_id=member.user_id, tag_name="diabetes"
            )
        )
        await service.unassign_tag(
            UnassignCommunityTagInput(
                community_id=community_id.value,
                acting_user_id=member.user_id,
                tag_id=summary.tag_id,
            )
        )
        assert await tags.is_assigned(community_id.value, summary.tag_id) is False

    async def test_unknown_tag_raises(self) -> None:
        service, _, community_id, member, _ = await _seeded()
        with pytest.raises(CommunityTagNotFoundError):
            await service.unassign_tag(
                UnassignCommunityTagInput(
                    community_id=community_id.value, acting_user_id=member.user_id, tag_id=uuid4()
                )
            )

    async def test_unassigned_tag_raises(self) -> None:
        service, tags, community_id, member, _ = await _seeded()
        tag = CommunityTag.create(name=CommunityTagName("diabetes"))
        await tags.add(tag)
        with pytest.raises(CommunityTagNotAssignedError):
            await service.unassign_tag(
                UnassignCommunityTagInput(
                    community_id=community_id.value, acting_user_id=member.user_id, tag_id=tag.id
                )
            )

    async def test_member_role_is_insufficient(self) -> None:
        service, _, community_id, member, _ = await _seeded(role=CommunityRole.MEMBER)
        with pytest.raises(InsufficientCommunityRoleError):
            await service.unassign_tag(
                UnassignCommunityTagInput(
                    community_id=community_id.value, acting_user_id=member.user_id, tag_id=uuid4()
                )
            )


class TestListTagsForCommunity:
    async def test_lists_only_assigned_tags(self) -> None:
        service, _, community_id, member, _ = await _seeded()
        assigned = await service.assign_tag(
            AssignCommunityTagInput(
                community_id=community_id.value, acting_user_id=member.user_id, tag_name="diabetes"
            )
        )
        results = await service.list_tags_for_community(community_id.value)
        assert [t.tag_id for t in results] == [assigned.tag_id]

    async def test_no_assigned_tags_returns_empty(self) -> None:
        service, _, community_id, _, _ = await _seeded()
        results = await service.list_tags_for_community(community_id.value)
        assert results == []


class TestSearchTags:
    async def test_matches_by_partial_name(self) -> None:
        service, tags, _, _, _ = await _seeded()
        await tags.add(CommunityTag.create(name=CommunityTagName("diabetes")))
        await tags.add(CommunityTag.create(name=CommunityTagName("oncology")))

        output = await service.search_tags(SearchCommunityTagsInput(query="diab"))
        assert output.total == 1
        assert output.items[0].name == "diabetes"

    async def test_no_matches_returns_empty(self) -> None:
        service, tags, _, _, _ = await _seeded()
        await tags.add(CommunityTag.create(name=CommunityTagName("diabetes")))

        output = await service.search_tags(SearchCommunityTagsInput(query="nephrology"))
        assert output.total == 0
        assert output.items == ()
