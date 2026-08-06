"""`GetPostService`/`ListPostsService` — read-only query services, the
same shape `app.modules.community.application.services
.community_query_service`/`app.modules.medical_topics.application
.services.topic_query_service` establish for their own analogous pairs
(plain classes, no `UnitOfWork`, no domain events — reads never mutate).

`GetPostService.get_by_id` is the one read path in this module that
enforces `PostVisibility` (see `_authorization.ensure_can_view`'s own
docstring) — every other read (`ListPostsService`, the `Browse*Feed`
services) is the management/moderator-facing view or is already
restricted to `PUBLISHED` posts by `browse_feed()` itself, so visibility
enforcement is this one method's own job.
"""

from uuid import UUID

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_posts.application.dto import (
    CommunityPostSummaryDTO,
    ListPostsInput,
    ListPostsOutput,
)
from app.modules.community_posts.application.services._authorization import ensure_can_view
from app.modules.community_posts.application.services._summary_mappers import post_to_summary
from app.modules.community_posts.domain.repositories import CommunityPostRepository


class GetPostService:
    def __init__(
        self, *, post_repository: CommunityPostRepository, community_query_port: CommunityQueryPort
    ) -> None:
        self._posts = post_repository
        self._communities = community_query_port

    async def get_by_id(
        self, post_id: UUID, *, acting_user_id: UUID | None = None
    ) -> CommunityPostSummaryDTO | None:
        post = await self._posts.get_by_id(post_id)
        if post is None:
            return None

        member = (
            await self._communities.get_membership(post.community_id, acting_user_id)
            if acting_user_id is not None
            else None
        )
        ensure_can_view(post, member, user_id=acting_user_id)

        return post_to_summary(post)

    async def get_by_slug(
        self, community_id: UUID, slug: str, *, acting_user_id: UUID | None = None
    ) -> CommunityPostSummaryDTO | None:
        post = await self._posts.get_by_slug(community_id, slug)
        if post is None:
            return None

        member = (
            await self._communities.get_membership(post.community_id, acting_user_id)
            if acting_user_id is not None
            else None
        )
        ensure_can_view(post, member, user_id=acting_user_id)

        return post_to_summary(post)


class ListPostsService:
    def __init__(self, *, post_repository: CommunityPostRepository) -> None:
        self._posts = post_repository

    async def list_posts(self, input_dto: ListPostsInput) -> ListPostsOutput:
        posts, total = await self._posts.search(
            organization_id=input_dto.organization_id,
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
            query=input_dto.query,
            include_deleted=input_dto.include_deleted,
            sort_by=input_dto.sort_by,
            sort_order=input_dto.sort_order,  # type: ignore[arg-type]
            offset=input_dto.offset,
            limit=input_dto.limit,
        )
        return ListPostsOutput(items=tuple(post_to_summary(p) for p in posts), total=total)
