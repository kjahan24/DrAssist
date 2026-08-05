"""`SearchCommunitiesService` — free-text search over community
name/description, optionally narrowed by category/tags. Distinct from
`BrowseCommunitiesService`: browsing filters by facets with no query
term (a directory view); searching always has a `query` (see that
service's own docstring for the full split).
"""

from app.modules.community.application.dto import SearchCommunitiesInput, SearchCommunitiesOutput
from app.modules.community.application.services._summary_mappers import community_to_summary
from app.modules.community.domain.repositories import CommunityRepository


class SearchCommunitiesService:
    def __init__(self, *, community_repository: CommunityRepository) -> None:
        self._communities = community_repository

    async def search(self, input_dto: SearchCommunitiesInput) -> SearchCommunitiesOutput:
        communities, total = await self._communities.search(
            organization_id=input_dto.organization_id,
            query=input_dto.query,
            category_id=input_dto.category_id,
            tag_ids=input_dto.tag_ids or None,
            offset=input_dto.offset,
            limit=input_dto.limit,
        )
        return SearchCommunitiesOutput(
            items=tuple(community_to_summary(c) for c in communities), total=total
        )
