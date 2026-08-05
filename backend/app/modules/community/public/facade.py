"""`CommunityFacade` — the one concrete implementation of
`CommunityQueryPort`. Constructed per-request by
`app.modules.community.container.build_community_facade`, bound to that
request's `AsyncSession`.
"""

from uuid import UUID

from app.modules.community.application.services.community_query_service import (
    CommunityMembershipQueryService,
    GetCommunityService,
)
from app.modules.community.public.dto import CommunityMemberSummaryDTO, CommunitySummaryDTO
from app.modules.community.public.interfaces import CommunityQueryPort


class CommunityFacade(CommunityQueryPort):
    def __init__(
        self,
        *,
        query_service: GetCommunityService,
        membership_query_service: CommunityMembershipQueryService,
    ) -> None:
        self._query_service = query_service
        self._membership_query_service = membership_query_service

    async def community_exists(self, community_id: UUID) -> bool:
        return await self._query_service.get_by_id(community_id) is not None

    async def get_community_summary(self, community_id: UUID) -> CommunitySummaryDTO | None:
        return await self._query_service.get_by_id(community_id)

    async def get_membership(
        self, community_id: UUID, user_id: UUID
    ) -> CommunityMemberSummaryDTO | None:
        return await self._membership_query_service.get_membership(community_id, user_id)

    async def is_active_member(self, community_id: UUID, user_id: UUID) -> bool:
        return await self._membership_query_service.is_active_member(community_id, user_id)
