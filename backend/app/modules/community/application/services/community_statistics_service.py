"""`CommunityStatisticsService` — aggregates a community's own member
count, moderator count, rule count, and tag count into one read model
(this task's own "Community statistics"/"Member count" FEATURES
bullets). Computed live from each owning repository rather than a
denormalized counter column on `Community` itself — avoiding the
"counter drifts out of sync with the rows it counts" class of bug, the
same "read-time aggregation, not a stored counter" choice this module
already made for `LeaveCommunityService`'s own owner-count check
(`CommunityMemberRepository.count_active_by_role`).
"""

from uuid import UUID

from app.modules.community.application.dto import CommunityStatisticsDTO
from app.modules.community.domain.enums import CommunityRole
from app.modules.community.domain.exceptions import CommunityNotFoundError
from app.modules.community.domain.repositories import (
    CommunityMemberRepository,
    CommunityRepository,
    CommunityRuleRepository,
    CommunityTagRepository,
)

_MODERATOR_ROLES = (CommunityRole.MODERATOR, CommunityRole.ADMIN, CommunityRole.OWNER)


class CommunityStatisticsService:
    def __init__(
        self,
        *,
        community_repository: CommunityRepository,
        community_member_repository: CommunityMemberRepository,
        community_rule_repository: CommunityRuleRepository,
        community_tag_repository: CommunityTagRepository,
    ) -> None:
        self._communities = community_repository
        self._members = community_member_repository
        self._rules = community_rule_repository
        self._tags = community_tag_repository

    async def get_statistics(self, community_id: UUID) -> CommunityStatisticsDTO:
        community = await self._communities.get_by_id(community_id)
        if community is None:
            raise CommunityNotFoundError(community_id)

        member_count = await self._members.count_active(community_id)
        moderator_members = await self._members.list_by_roles(
            community_id, _MODERATOR_ROLES, limit=10_000
        )
        rules = await self._rules.list_by_community(community_id)
        tags = await self._tags.list_for_community(community_id)

        return CommunityStatisticsDTO(
            community_id=community_id,
            member_count=member_count,
            moderator_count=len(moderator_members),
            rule_count=len(rules),
            tag_count=len(tags),
            is_verified=community.is_verified,
            is_featured=community.is_featured,
            created_at=community.created_at,
        )
