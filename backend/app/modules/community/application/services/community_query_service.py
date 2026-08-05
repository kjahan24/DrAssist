"""`GetCommunityService`/`ListCommunitiesService`/
`CommunityMembershipQueryService` — read-only query services, the same
shape `app.modules.organization.application.services
.organization_query_service` establishes for its own
`OrganizationQueryService`/`DepartmentQueryService` pair (plain classes,
no `UnitOfWork`, no domain events — reads never mutate).

`CommunityMembershipQueryService` backs `public/facade.py`'s own
`get_membership`/`is_active_member` — the membership-lookup half of the
public query port future Posts/Questions/etc. modules will depend on;
see `public/interfaces.py`'s own docstring. Its own `list_moderators`
backs this task's own "Community moderators" feature.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.community.application.dto import (
    CommunityCategorySummaryDTO,
    CommunityMemberSummaryDTO,
    CommunitySummaryDTO,
    ListCommunitiesOutput,
)
from app.modules.community.application.services._summary_mappers import (
    category_to_summary,
    community_to_summary,
    member_to_summary,
)
from app.modules.community.domain.enums import (
    CommunityMemberStatus,
    CommunityRole,
    CommunityVisibility,
)
from app.modules.community.domain.repositories import (
    CommunityCategoryRepository,
    CommunityMemberRepository,
    CommunityRepository,
)

_MODERATOR_ROLES = (CommunityRole.MODERATOR, CommunityRole.ADMIN, CommunityRole.OWNER)


class GetCommunityService:
    def __init__(self, *, community_repository: CommunityRepository) -> None:
        self._communities = community_repository

    async def get_by_id(self, community_id: UUID) -> CommunitySummaryDTO | None:
        community = await self._communities.get_by_id(community_id)
        return community_to_summary(community) if community is not None else None

    async def get_by_slug(self, organization_id: UUID, slug: str) -> CommunitySummaryDTO | None:
        community = await self._communities.get_by_slug(organization_id, slug)
        return community_to_summary(community) if community is not None else None


class ListCommunitiesService:
    def __init__(self, *, community_repository: CommunityRepository) -> None:
        self._communities = community_repository

    async def list_communities(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        visibilities: Sequence[CommunityVisibility] | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> ListCommunitiesOutput:
        communities, total = await self._communities.search(
            organization_id=organization_id,
            query=query,
            visibilities=visibilities,
            created_from=created_from,
            created_to=created_to,
            updated_from=updated_from,
            updated_to=updated_to,
            include_deleted=include_deleted,
            sort_by=sort_by,
            sort_order=sort_order,
            offset=offset,
            limit=limit,
        )
        return ListCommunitiesOutput(
            items=tuple(community_to_summary(c) for c in communities), total=total
        )


class CommunityMembershipQueryService:
    def __init__(self, *, community_member_repository: CommunityMemberRepository) -> None:
        self._members = community_member_repository

    async def get_membership(
        self, community_id: UUID, user_id: UUID
    ) -> CommunityMemberSummaryDTO | None:
        member = await self._members.get_by_community_and_user(community_id, user_id)
        return member_to_summary(member) if member is not None else None

    async def is_active_member(self, community_id: UUID, user_id: UUID) -> bool:
        member = await self._members.get_by_community_and_user(community_id, user_id)
        return member is not None and member.status is CommunityMemberStatus.ACTIVE

    async def list_moderators(
        self, community_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[CommunityMemberSummaryDTO]:
        members = await self._members.list_by_roles(
            community_id, _MODERATOR_ROLES, offset=offset, limit=limit
        )
        return [member_to_summary(m) for m in members]


class CommunityCategoryQueryService:
    def __init__(self, *, community_category_repository: CommunityCategoryRepository) -> None:
        self._categories = community_category_repository

    async def list_active(
        self, *, offset: int = 0, limit: int = 100
    ) -> list[CommunityCategorySummaryDTO]:
        categories = await self._categories.list_active(offset=offset, limit=limit)
        return [category_to_summary(c) for c in categories]
