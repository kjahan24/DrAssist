"""Unit tests for `ManageCommunityRulesService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.application.dto import (
    CreateCommunityRuleInput,
    DeleteCommunityRuleInput,
    ReorderCommunityRulesInput,
    SetCommunityRuleEnabledInput,
    UpdateCommunityRuleInput,
)
from app.modules.community.application.services.manage_community_rules_service import (
    ManageCommunityRulesService,
)
from app.modules.community.domain.entities import CommunityMember
from app.modules.community.domain.enums import CommunityRole
from app.modules.community.domain.events import (
    CommunityRuleCreated,
    CommunityRuleEnabledChanged,
    CommunityRulesReordered,
    CommunityRuleUpdated,
)
from app.modules.community.domain.exceptions import (
    CommunityMembershipNotFoundError,
    CommunityRuleNotFoundError,
    InsufficientCommunityRoleError,
)
from app.modules.community.domain.value_objects import CommunityId
from tests.unit.modules.community.application.fakes import (
    FakeCommunityMemberRepository,
    FakeCommunityRuleRepository,
    FakeUnitOfWork,
)


async def _seeded(
    role: CommunityRole = CommunityRole.ADMIN,
) -> tuple[
    ManageCommunityRulesService,
    FakeCommunityRuleRepository,
    CommunityId,
    CommunityMember,
    FakeUnitOfWork,
]:
    rules = FakeCommunityRuleRepository()
    members = FakeCommunityMemberRepository()
    uow = FakeUnitOfWork()
    service = ManageCommunityRulesService(
        community_rule_repository=rules, community_member_repository=members, unit_of_work=uow
    )

    community_id = CommunityId(uuid4())
    acting_user_id = uuid4()
    member = CommunityMember.create(community_id=community_id, user_id=acting_user_id, role=role)
    await members.add(member)

    return service, rules, community_id, member, uow


class TestCreateRule:
    async def test_creates_a_rule_with_position_zero(self) -> None:
        service, rules, community_id, member, _ = await _seeded()
        output = await service.create_rule(
            CreateCommunityRuleInput(
                community_id=community_id.value,
                acting_user_id=member.user_id,
                title="Be respectful",
            )
        )
        assert output.position == 0
        stored = await rules.get_by_id(output.rule_id)
        assert stored is not None
        assert str(stored.title) == "Be respectful"

    async def test_second_rule_gets_the_next_position(self) -> None:
        service, _, community_id, member, _ = await _seeded()
        await service.create_rule(
            CreateCommunityRuleInput(
                community_id=community_id.value, acting_user_id=member.user_id, title="Rule one"
            )
        )
        second = await service.create_rule(
            CreateCommunityRuleInput(
                community_id=community_id.value, acting_user_id=member.user_id, title="Rule two"
            )
        )
        assert second.position == 1

    async def test_accepts_a_description(self) -> None:
        service, rules, community_id, member, _ = await _seeded()
        output = await service.create_rule(
            CreateCommunityRuleInput(
                community_id=community_id.value,
                acting_user_id=member.user_id,
                title="Be respectful",
                description="No harassment.",
            )
        )
        stored = await rules.get_by_id(output.rule_id)
        assert stored is not None
        assert stored.description == "No harassment."

    async def test_member_role_is_insufficient(self) -> None:
        service, _, community_id, member, _ = await _seeded(role=CommunityRole.MEMBER)
        with pytest.raises(InsufficientCommunityRoleError):
            await service.create_rule(
                CreateCommunityRuleInput(
                    community_id=community_id.value, acting_user_id=member.user_id, title="Rule"
                )
            )

    async def test_acting_user_with_no_membership_raises(self) -> None:
        service, _, community_id, _, _ = await _seeded()
        with pytest.raises(CommunityMembershipNotFoundError):
            await service.create_rule(
                CreateCommunityRuleInput(
                    community_id=community_id.value, acting_user_id=uuid4(), title="Rule"
                )
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, community_id, member, uow = await _seeded()
        await service.create_rule(
            CreateCommunityRuleInput(
                community_id=community_id.value, acting_user_id=member.user_id, title="Rule"
            )
        )
        assert uow.committed is True

    async def test_publishes_a_community_rule_created_event(self) -> None:
        service, _, community_id, member, uow = await _seeded()
        await service.create_rule(
            CreateCommunityRuleInput(
                community_id=community_id.value, acting_user_id=member.user_id, title="Rule"
            )
        )
        assert any(isinstance(e, CommunityRuleCreated) for e in uow.published_events)


class TestUpdateRule:
    async def test_updates_the_title(self) -> None:
        service, rules, community_id, member, _ = await _seeded()
        created = await service.create_rule(
            CreateCommunityRuleInput(
                community_id=community_id.value, acting_user_id=member.user_id, title="Original"
            )
        )
        await service.update_rule(
            UpdateCommunityRuleInput(
                rule_id=created.rule_id,
                community_id=community_id.value,
                acting_user_id=member.user_id,
                title="Updated",
            )
        )
        stored = await rules.get_by_id(created.rule_id)
        assert stored is not None
        assert str(stored.title) == "Updated"

    async def test_updates_the_description(self) -> None:
        service, rules, community_id, member, _ = await _seeded()
        created = await service.create_rule(
            CreateCommunityRuleInput(
                community_id=community_id.value, acting_user_id=member.user_id, title="Rule"
            )
        )
        await service.update_rule(
            UpdateCommunityRuleInput(
                rule_id=created.rule_id,
                community_id=community_id.value,
                acting_user_id=member.user_id,
                description="Updated description.",
            )
        )
        stored = await rules.get_by_id(created.rule_id)
        assert stored is not None
        assert stored.description == "Updated description."

    async def test_unknown_rule_raises(self) -> None:
        service, _, community_id, member, _ = await _seeded()
        with pytest.raises(CommunityRuleNotFoundError):
            await service.update_rule(
                UpdateCommunityRuleInput(
                    rule_id=uuid4(),
                    community_id=community_id.value,
                    acting_user_id=member.user_id,
                    title="X",
                )
            )

    async def test_rule_from_a_different_community_raises(self) -> None:
        """The caller must be an admin of the *other* community too — a
        rule lookup mismatch is only reachable past `_ensure_admin`'s own
        membership check, which is keyed on `input_dto.community_id`."""
        rules = FakeCommunityRuleRepository()
        members = FakeCommunityMemberRepository()
        uow = FakeUnitOfWork()
        service = ManageCommunityRulesService(
            community_rule_repository=rules, community_member_repository=members, unit_of_work=uow
        )

        community_id = CommunityId(uuid4())
        other_community_id = CommunityId(uuid4())
        acting_user_id = uuid4()
        await members.add(
            CommunityMember.create(
                community_id=community_id, user_id=acting_user_id, role=CommunityRole.ADMIN
            )
        )
        await members.add(
            CommunityMember.create(
                community_id=other_community_id, user_id=acting_user_id, role=CommunityRole.ADMIN
            )
        )

        created = await service.create_rule(
            CreateCommunityRuleInput(
                community_id=community_id.value, acting_user_id=acting_user_id, title="Rule"
            )
        )
        with pytest.raises(CommunityRuleNotFoundError):
            await service.update_rule(
                UpdateCommunityRuleInput(
                    rule_id=created.rule_id,
                    community_id=other_community_id.value,
                    acting_user_id=acting_user_id,
                    title="X",
                )
            )

    async def test_member_role_is_insufficient(self) -> None:
        service, _, community_id, member, _ = await _seeded(role=CommunityRole.MEMBER)
        with pytest.raises(InsufficientCommunityRoleError):
            await service.update_rule(
                UpdateCommunityRuleInput(
                    rule_id=uuid4(),
                    community_id=community_id.value,
                    acting_user_id=member.user_id,
                    title="X",
                )
            )

    async def test_publishes_a_community_rule_updated_event(self) -> None:
        service, _, community_id, member, uow = await _seeded()
        created = await service.create_rule(
            CreateCommunityRuleInput(
                community_id=community_id.value, acting_user_id=member.user_id, title="Rule"
            )
        )
        await service.update_rule(
            UpdateCommunityRuleInput(
                rule_id=created.rule_id,
                community_id=community_id.value,
                acting_user_id=member.user_id,
                title="Updated",
            )
        )
        assert any(isinstance(e, CommunityRuleUpdated) for e in uow.published_events)


class TestSetEnabled:
    async def test_disables_a_rule(self) -> None:
        service, rules, community_id, member, _ = await _seeded()
        created = await service.create_rule(
            CreateCommunityRuleInput(
                community_id=community_id.value, acting_user_id=member.user_id, title="Rule"
            )
        )
        await service.set_enabled(
            SetCommunityRuleEnabledInput(
                rule_id=created.rule_id,
                community_id=community_id.value,
                acting_user_id=member.user_id,
                enabled=False,
            )
        )
        stored = await rules.get_by_id(created.rule_id)
        assert stored is not None
        assert stored.is_enabled is False

    async def test_unknown_rule_raises(self) -> None:
        service, _, community_id, member, _ = await _seeded()
        with pytest.raises(CommunityRuleNotFoundError):
            await service.set_enabled(
                SetCommunityRuleEnabledInput(
                    rule_id=uuid4(),
                    community_id=community_id.value,
                    acting_user_id=member.user_id,
                    enabled=False,
                )
            )

    async def test_member_role_is_insufficient(self) -> None:
        service, _, community_id, member, _ = await _seeded(role=CommunityRole.MEMBER)
        with pytest.raises(InsufficientCommunityRoleError):
            await service.set_enabled(
                SetCommunityRuleEnabledInput(
                    rule_id=uuid4(),
                    community_id=community_id.value,
                    acting_user_id=member.user_id,
                    enabled=False,
                )
            )

    async def test_publishes_a_community_rule_enabled_changed_event(self) -> None:
        service, _, community_id, member, uow = await _seeded()
        created = await service.create_rule(
            CreateCommunityRuleInput(
                community_id=community_id.value, acting_user_id=member.user_id, title="Rule"
            )
        )
        await service.set_enabled(
            SetCommunityRuleEnabledInput(
                rule_id=created.rule_id,
                community_id=community_id.value,
                acting_user_id=member.user_id,
                enabled=False,
            )
        )
        assert any(isinstance(e, CommunityRuleEnabledChanged) for e in uow.published_events)


class TestDeleteRule:
    async def test_removes_the_rule(self) -> None:
        service, rules, community_id, member, _ = await _seeded()
        created = await service.create_rule(
            CreateCommunityRuleInput(
                community_id=community_id.value, acting_user_id=member.user_id, title="Rule"
            )
        )
        await service.delete_rule(
            DeleteCommunityRuleInput(
                rule_id=created.rule_id,
                community_id=community_id.value,
                acting_user_id=member.user_id,
            )
        )
        assert await rules.get_by_id(created.rule_id) is None

    async def test_unknown_rule_raises(self) -> None:
        service, _, community_id, member, _ = await _seeded()
        with pytest.raises(CommunityRuleNotFoundError):
            await service.delete_rule(
                DeleteCommunityRuleInput(
                    rule_id=uuid4(), community_id=community_id.value, acting_user_id=member.user_id
                )
            )

    async def test_member_role_is_insufficient(self) -> None:
        service, _, community_id, member, _ = await _seeded(role=CommunityRole.MEMBER)
        with pytest.raises(InsufficientCommunityRoleError):
            await service.delete_rule(
                DeleteCommunityRuleInput(
                    rule_id=uuid4(), community_id=community_id.value, acting_user_id=member.user_id
                )
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, community_id, member, uow = await _seeded()
        created = await service.create_rule(
            CreateCommunityRuleInput(
                community_id=community_id.value, acting_user_id=member.user_id, title="Rule"
            )
        )
        await service.delete_rule(
            DeleteCommunityRuleInput(
                rule_id=created.rule_id,
                community_id=community_id.value,
                acting_user_id=member.user_id,
            )
        )
        assert uow.committed is True


class TestReorderRules:
    async def test_reorders_rules_by_the_given_order(self) -> None:
        service, rules, community_id, member, _ = await _seeded()
        first = await service.create_rule(
            CreateCommunityRuleInput(
                community_id=community_id.value, acting_user_id=member.user_id, title="First"
            )
        )
        second = await service.create_rule(
            CreateCommunityRuleInput(
                community_id=community_id.value, acting_user_id=member.user_id, title="Second"
            )
        )
        await service.reorder(
            ReorderCommunityRulesInput(
                community_id=community_id.value,
                acting_user_id=member.user_id,
                ordered_rule_ids=[second.rule_id, first.rule_id],
            )
        )
        reordered_second = await rules.get_by_id(second.rule_id)
        reordered_first = await rules.get_by_id(first.rule_id)
        assert reordered_second is not None
        assert reordered_first is not None
        assert reordered_second.position == 0
        assert reordered_first.position == 1

    async def test_unknown_rule_id_raises(self) -> None:
        service, _, community_id, member, _ = await _seeded()
        await service.create_rule(
            CreateCommunityRuleInput(
                community_id=community_id.value, acting_user_id=member.user_id, title="Rule"
            )
        )
        with pytest.raises(CommunityRuleNotFoundError):
            await service.reorder(
                ReorderCommunityRulesInput(
                    community_id=community_id.value,
                    acting_user_id=member.user_id,
                    ordered_rule_ids=[uuid4()],
                )
            )

    async def test_member_role_is_insufficient(self) -> None:
        service, _, community_id, member, _ = await _seeded(role=CommunityRole.MEMBER)
        with pytest.raises(InsufficientCommunityRoleError):
            await service.reorder(
                ReorderCommunityRulesInput(
                    community_id=community_id.value,
                    acting_user_id=member.user_id,
                    ordered_rule_ids=[],
                )
            )

    async def test_publishes_a_single_community_rules_reordered_event(self) -> None:
        service, _, community_id, member, uow = await _seeded()
        first = await service.create_rule(
            CreateCommunityRuleInput(
                community_id=community_id.value, acting_user_id=member.user_id, title="First"
            )
        )
        second = await service.create_rule(
            CreateCommunityRuleInput(
                community_id=community_id.value, acting_user_id=member.user_id, title="Second"
            )
        )
        await service.reorder(
            ReorderCommunityRulesInput(
                community_id=community_id.value,
                acting_user_id=member.user_id,
                ordered_rule_ids=[second.rule_id, first.rule_id],
            )
        )
        reorder_events = [e for e in uow.published_events if isinstance(e, CommunityRulesReordered)]
        assert len(reorder_events) == 1
        assert reorder_events[0].rule_ids == (second.rule_id, first.rule_id)


class TestListRules:
    async def test_lists_rules_ordered_by_position(self) -> None:
        service, _, community_id, member, _ = await _seeded()
        first = await service.create_rule(
            CreateCommunityRuleInput(
                community_id=community_id.value, acting_user_id=member.user_id, title="First"
            )
        )
        second = await service.create_rule(
            CreateCommunityRuleInput(
                community_id=community_id.value, acting_user_id=member.user_id, title="Second"
            )
        )
        results = await service.list_rules(community_id.value)
        assert [r.rule_id for r in results] == [first.rule_id, second.rule_id]

    async def test_excludes_disabled_rules_when_requested(self) -> None:
        service, _, community_id, member, _ = await _seeded()
        enabled = await service.create_rule(
            CreateCommunityRuleInput(
                community_id=community_id.value, acting_user_id=member.user_id, title="Enabled"
            )
        )
        disabled = await service.create_rule(
            CreateCommunityRuleInput(
                community_id=community_id.value, acting_user_id=member.user_id, title="Disabled"
            )
        )
        await service.set_enabled(
            SetCommunityRuleEnabledInput(
                rule_id=disabled.rule_id,
                community_id=community_id.value,
                acting_user_id=member.user_id,
                enabled=False,
            )
        )
        results = await service.list_rules(community_id.value, include_disabled=False)
        assert [r.rule_id for r in results] == [enabled.rule_id]
