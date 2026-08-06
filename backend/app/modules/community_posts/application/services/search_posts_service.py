"""`SearchPostsService` — full-filter keyword search over posts, backing
this task's own SEARCH section. Distinct from the `Browse*Feed` services:
those are the cursor-paginated, `PUBLISHED`-only consumer feeds; this is
the offset-paginated, unrestricted-by-status management/search view — the
same split `app.modules.community.application.services
.search_communities_service.SearchCommunitiesService` draws against
`BrowseCommunitiesService` for itself.
"""

from app.modules.community_posts.application.dto import SearchPostsInput, SearchPostsOutput
from app.modules.community_posts.application.services._summary_mappers import post_to_summary
from app.modules.community_posts.domain.repositories import CommunityPostRepository


class SearchPostsService:
    def __init__(self, *, post_repository: CommunityPostRepository) -> None:
        self._posts = post_repository

    async def search(self, input_dto: SearchPostsInput) -> SearchPostsOutput:
        posts, total = await self._posts.search(
            organization_id=input_dto.organization_id,
            query=input_dto.query,
            community_id=input_dto.community_id,
            topic_id=input_dto.topic_id,
            author_id=input_dto.author_id,
            post_type=input_dto.post_type,
            status=input_dto.status,
            visibility=input_dto.visibility,
            pinned_only=input_dto.pinned_only,
            featured_only=input_dto.featured_only,
            created_from=input_dto.created_from,
            created_to=input_dto.created_to,
            offset=input_dto.offset,
            limit=input_dto.limit,
        )
        return SearchPostsOutput(items=tuple(post_to_summary(p) for p in posts), total=total)
