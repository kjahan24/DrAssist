"""`FeatureCommunitiesService` — platform-level curation: listing
featured communities, and toggling a community's own `is_featured`/
`is_verified` flags.

Deliberately **not** authorized via `ensure_role_at_least` (the
per-community role check every other mutating service in this module
uses): "featured"/"verified" are platform-wide trust/promotion signals a
community's own `OWNER` must not be able to grant themselves — a
self-service "mark my own community verified" button would make
"verified" meaningless. Authorization instead happens at the API layer,
via `app.api.deps.require_permission("communities.feature"
/"communities.verify")` — the first real use of that already-built,
previously-unused RBAC dependency in this codebase (see
`app/api/deps.py`'s own docstring); registering those permission codes
against an actual platform-admin role is an Authentication-module/
operational concern outside this module's own scope, the same way no
`Permission` row is seeded by any application code today (confirmed:
`b22ab71b3d39_extend_roles_and_permissions_for_rbac.py`'s own docstring
notes `permissions` starts empty).
"""

from app.modules.community.application.dto import (
    BrowseCommunitiesOutput,
    ListFeaturedCommunitiesInput,
    SetCommunityFeaturedInput,
    SetCommunityVerifiedInput,
)
from app.modules.community.application.services._summary_mappers import community_to_summary
from app.modules.community.domain.enums import CommunityVisibility
from app.modules.community.domain.exceptions import CommunityNotFoundError
from app.modules.community.domain.repositories import CommunityRepository
from app.shared.application.unit_of_work import UnitOfWork


class FeatureCommunitiesService:
    def __init__(
        self, *, community_repository: CommunityRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._communities = community_repository
        self._uow = unit_of_work

    async def list_featured(
        self, input_dto: ListFeaturedCommunitiesInput
    ) -> BrowseCommunitiesOutput:
        communities, total = await self._communities.search(
            organization_id=input_dto.organization_id,
            featured_only=True,
            visibilities=(CommunityVisibility.PUBLIC,),
            offset=input_dto.offset,
            limit=input_dto.limit,
        )
        return BrowseCommunitiesOutput(
            items=tuple(community_to_summary(c) for c in communities), total=total
        )

    async def set_featured(self, input_dto: SetCommunityFeaturedInput) -> None:
        community = await self._communities.get_by_id(input_dto.community_id)
        if community is None:
            raise CommunityNotFoundError(input_dto.community_id)
        community.set_featured(input_dto.featured)
        await self._communities.add(community)
        self._uow.collect_events(community.pull_events())
        await self._uow.commit()

    async def set_verified(self, input_dto: SetCommunityVerifiedInput) -> None:
        community = await self._communities.get_by_id(input_dto.community_id)
        if community is None:
            raise CommunityNotFoundError(input_dto.community_id)
        community.set_verified(input_dto.verified)
        await self._communities.add(community)
        self._uow.collect_events(community.pull_events())
        await self._uow.commit()
