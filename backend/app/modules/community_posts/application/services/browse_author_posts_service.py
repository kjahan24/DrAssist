"""`BrowseAuthorPostsService` — one author's own published post history,
across every community in the caller's own organization (cursor-
paginated — see `CommunityPostRepository.browse_feed`'s own docstring).
"""

from app.modules.community_posts.application.dto import BrowseAuthorPostsInput, PostFeedOutput
from app.modules.community_posts.application.services._summary_mappers import post_to_summary
from app.modules.community_posts.domain.repositories import CommunityPostRepository


class BrowseAuthorPostsService:
    def __init__(self, *, post_repository: CommunityPostRepository) -> None:
        self._posts = post_repository

    async def browse(self, input_dto: BrowseAuthorPostsInput) -> PostFeedOutput:
        posts, next_cursor = await self._posts.browse_feed(
            organization_id=input_dto.organization_id,
            author_id=input_dto.author_id,
            cursor=input_dto.cursor,
            limit=input_dto.limit,
        )
        return PostFeedOutput(
            items=tuple(post_to_summary(p) for p in posts), next_cursor=next_cursor
        )
