"""Unit tests for `CommunityStatisticsService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.application.services.community_statistics_service import (
    CommunityStatisticsService,
)
from app.modules.community.domain.entities import (
    Community,
    CommunityMember,
    CommunityRule,
    CommunityTag,
)
from app.modules.community.domain.enums import CommunityRole
from app.modules.community.domain.exceptions import CommunityNotFoundError
from app.modules.community.domain.value_objects import (
    CommunityId,
    CommunityName,
    CommunityRuleTitle,
    CommunitySlug,
    CommunityTagName,
)
from tests.unit.modules.community.application.fakes import (
    FakeCommunityMemberRepository,
    FakeCommunityRepository,
    FakeCommunityRuleRepository,
    FakeCommunityTagRepository,
)


async def _seeded() -> (
    tuple[
        CommunityStatisticsService,
        Community,
        FakeCommunityMemberRepository,
        FakeCommunityRuleRepository,
        FakeCommunityTagRepository,
    ]
):
    communities = FakeCommunityRepository()
    members = FakeCommunityMemberRepository()
    rules = FakeCommunityRuleRepository()
    tags = FakeCommunityTagRepository()
    service = CommunityStatisticsService(
        community_repository=communities,
        community_member_repository=members,
        community_rule_repository=rules,
        community_tag_repository=tags,
    )

    community = Community.create(
        organization_id=uuid4(), slug=CommunitySlug("oncology"), name=CommunityName("Oncology")
    )
    await communities.add(community)

    return service, community, members, rules, tags


class TestCommunityStatistics:
    async def test_counts_active_members(self) -> None:
        service, community, members, _, _ = await _seeded()
        community_id = CommunityId(community.id)
        await members.add(CommunityMember.create(community_id=community_id, user_id=uuid4()))
        await members.add(CommunityMember.create(community_id=community_id, user_id=uuid4()))
        left_member = CommunityMember.create(community_id=community_id, user_id=uuid4())
        left_member.leave()
        await members.add(left_member)

        stats = await service.get_statistics(community.id)
        assert stats.member_count == 2

    async def test_counts_moderators_admins_and_owners_as_moderators(self) -> None:
        service, community, members, _, _ = await _seeded()
        community_id = CommunityId(community.id)
        await members.add(
            CommunityMember.create(
                community_id=community_id, user_id=uuid4(), role=CommunityRole.MODERATOR
            )
        )
        await members.add(
            CommunityMember.create(
                community_id=community_id, user_id=uuid4(), role=CommunityRole.ADMIN
            )
        )
        await members.add(
            CommunityMember.create(
                community_id=community_id, user_id=uuid4(), role=CommunityRole.OWNER
            )
        )
        await members.add(
            CommunityMember.create(
                community_id=community_id, user_id=uuid4(), role=CommunityRole.MEMBER
            )
        )

        stats = await service.get_statistics(community.id)
        assert stats.moderator_count == 3

    async def test_counts_rules(self) -> None:
        service, community, _, rules, _ = await _seeded()
        community_id = CommunityId(community.id)
        await rules.add(
            CommunityRule.create(community_id=community_id, title=CommunityRuleTitle("Rule 1"))
        )
        await rules.add(
            CommunityRule.create(community_id=community_id, title=CommunityRuleTitle("Rule 2"))
        )

        stats = await service.get_statistics(community.id)
        assert stats.rule_count == 2

    async def test_counts_tags(self) -> None:
        service, community, _, _, tags = await _seeded()
        tag = CommunityTag.create(name=CommunityTagName("diabetes"))
        await tags.add(tag)
        await tags.assign(community.id, tag.id)

        stats = await service.get_statistics(community.id)
        assert stats.tag_count == 1

    async def test_reflects_verified_and_featured_flags(self) -> None:
        service, community, _, _, _ = await _seeded()
        community.set_verified(True)
        community.set_featured(True)

        stats = await service.get_statistics(community.id)
        assert stats.is_verified is True
        assert stats.is_featured is True

    async def test_reflects_created_at(self) -> None:
        service, community, _, _, _ = await _seeded()
        stats = await service.get_statistics(community.id)
        assert stats.created_at == community.created_at

    async def test_no_members_rules_or_tags_returns_zero_counts(self) -> None:
        service, community, _, _, _ = await _seeded()
        stats = await service.get_statistics(community.id)
        assert stats.member_count == 0
        assert stats.moderator_count == 0
        assert stats.rule_count == 0
        assert stats.tag_count == 0

    async def test_unknown_community_raises(self) -> None:
        service, _, _, _, _ = await _seeded()
        with pytest.raises(CommunityNotFoundError):
            await service.get_statistics(uuid4())
