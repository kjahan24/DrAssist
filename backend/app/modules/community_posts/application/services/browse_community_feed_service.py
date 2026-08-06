"""`BrowseCommunityFeedService` — the Reddit-style per-community feed,
cursor-paginated (see `CommunityPostRepository.browse_feed`'s own
docstring), with pinned posts sorted first (`pinned_first=True` — see
`CommunityPost.set_pinned`'s own docstring for why this is the one
`browse_feed` caller that sets it)."""

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_posts.application.dto import BrowseCommunityFeedInput, PostFeedOutput
from app.modules.community_posts.application.services._summary_mappers import post_to_summary
from app.modules.community_posts.domain.exceptions import CommunityNotFoundForPostError
from app.modules.community_posts.domain.repositories import CommunityPostRepository


class BrowseCommunityFeedService:
    def __init__(
        self, *, post_repository: CommunityPostRepository, community_query_port: CommunityQueryPort
    ) -> None:
        self._posts = post_repository
        self._communities = community_query_port

    async def browse(self, input_dto: BrowseCommunityFeedInput) -> PostFeedOutput:
        community = await self._communities.get_community_summary(input_dto.community_id)
        if community is None:
            raise CommunityNotFoundForPostError(input_dto.community_id)

        posts, next_cursor = await self._posts.browse_feed(
            organization_id=community.organization_id,
            community_id=input_dto.community_id,
            pinned_first=True,
            cursor=input_dto.cursor,
            limit=input_dto.limit,
        )
        return PostFeedOutput(
            items=tuple(post_to_summary(p) for p in posts), next_cursor=next_cursor
        )
