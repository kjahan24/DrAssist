"""`PostFacade` — the one concrete implementation of `PostQueryPort`.
Constructed per-request by
`app.modules.community_posts.container.build_post_facade`, bound to that
request's `AsyncSession`.

Deliberately built directly against `CommunityPostRepository`, not
`GetPostService` — `GetPostService.get_by_id` enforces `PostVisibility`
for an end-user caller (see `_authorization.ensure_can_view`'s own
docstring), which doesn't apply to a module-to-module existence/summary
check with no acting user in the picture.
"""

from uuid import UUID

from app.modules.community_posts.application.services._summary_mappers import post_to_summary
from app.modules.community_posts.domain.repositories import CommunityPostRepository
from app.modules.community_posts.public.dto import CommunityPostSummaryDTO
from app.modules.community_posts.public.interfaces import PostQueryPort


class PostFacade(PostQueryPort):
    def __init__(self, *, post_repository: CommunityPostRepository) -> None:
        self._posts = post_repository

    async def post_exists(self, post_id: UUID) -> bool:
        return await self._posts.get_by_id(post_id) is not None

    async def get_post_summary(self, post_id: UUID) -> CommunityPostSummaryDTO | None:
        post = await self._posts.get_by_id(post_id)
        return post_to_summary(post) if post is not None else None
