"""`BrowseCommunitiesService` — facet-driven discovery (category, tags,
visibility) with a choice of sort, covering this task's own "Browse
communities"/"Popular communities"/"Recently created communities"
FEATURES bullets as three sort modes of the *same* browsing capability,
rather than three separate near-duplicate use cases — "Popular"/"Recent"
are not named in this task's own APPLICATION section (only
`BrowseCommunities` is), so they're delivered as `sort` values here
instead of inventing unrequested top-level classes.

Distinct from `SearchCommunitiesService`: browsing filters by facets
with no free-text term (a directory/catalog view); searching matches a
query string against name/description (see that service's own
docstring). Both share `CommunityRepository.search()` underneath.
"""

from app.modules.community.application.dto import BrowseCommunitiesInput, BrowseCommunitiesOutput
from app.modules.community.application.services._summary_mappers import community_to_summary
from app.modules.community.domain.repositories import CommunityRepository

_SORT_COLUMNS = {"recent": "created_at", "popular": "member_count", "alphabetical": "name"}
_SORT_ORDERS = {"recent": "desc", "popular": "desc", "alphabetical": "asc"}


class BrowseCommunitiesService:
    def __init__(self, *, community_repository: CommunityRepository) -> None:
        self._communities = community_repository

    async def browse(self, input_dto: BrowseCommunitiesInput) -> BrowseCommunitiesOutput:
        sort_by = _SORT_COLUMNS.get(input_dto.sort, "created_at")
        sort_order = _SORT_ORDERS.get(input_dto.sort, "desc")

        communities, total = await self._communities.search(
            organization_id=input_dto.organization_id,
            visibilities=input_dto.visibilities,
            category_id=input_dto.category_id,
            tag_ids=input_dto.tag_ids or None,
            sort_by=sort_by,
            sort_order=sort_order,  # type: ignore[arg-type]
            offset=input_dto.offset,
            limit=input_dto.limit,
        )
        return BrowseCommunitiesOutput(
            items=tuple(community_to_summary(c) for c in communities), total=total
        )
