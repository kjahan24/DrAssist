"""`GetCommentService` — the one read path in this module that enforces
comment-level viewability (see `_authorization.ensure_can_view`'s own
docstring); every listing/searching/thread service is already restricted
to `PUBLISHED` comments by its own repository query, the same "read
paths differ in how they gate visibility" split
`app.modules.community_answers.application.services.answer_query_service`
already establishes for itself."""

from uuid import UUID

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_comments.application.dto import CommunityCommentSummaryDTO
from app.modules.community_comments.application.services._authorization import ensure_can_view
from app.modules.community_comments.application.services._summary_mappers import (
    comment_to_summary,
)
from app.modules.community_comments.domain.repositories import CommunityCommentRepository


class GetCommentService:
    def __init__(
        self,
        *,
        comment_repository: CommunityCommentRepository,
        community_query_port: CommunityQueryPort,
    ) -> None:
        self._comments = comment_repository
        self._communities = community_query_port

    async def get_by_id(
        self, comment_id: UUID, *, acting_user_id: UUID | None = None
    ) -> CommunityCommentSummaryDTO | None:
        comment = await self._comments.get_by_id(comment_id)
        if comment is None:
            return None

        member = (
            await self._communities.get_membership(comment.community_id, acting_user_id)
            if acting_user_id is not None
            else None
        )
        ensure_can_view(comment, member, user_id=acting_user_id)

        return comment_to_summary(comment)
