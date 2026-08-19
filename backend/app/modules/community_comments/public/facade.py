"""`CommentFacade` — the one concrete implementation of
`CommentQueryPort`. Constructed per-request by
`app.modules.community_comments.container.build_comment_facade`, bound
to that request's `AsyncSession`.

Deliberately built directly against `CommunityCommentRepository`, not
`GetCommentService` — `GetCommentService.get_by_id` enforces comment
viewability for an end-user caller, which doesn't apply to a
module-to-module existence/summary check with no acting user in the
picture — the same reasoning `app.modules.community_answers.public
.facade.AnswerFacade` already establishes for itself.

Reuses `_summary_mappers.comment_to_summary` unchanged, so a
module-to-module summary lookup masks `author_id` for an anonymous
comment exactly like every other read path in this module — see that
mapper's own docstring.
"""

from uuid import UUID

from app.modules.community_comments.application.services._summary_mappers import (
    comment_to_summary,
)
from app.modules.community_comments.domain.entities import MAX_COMMENT_DEPTH
from app.modules.community_comments.domain.repositories import CommunityCommentRepository
from app.modules.community_comments.public.dto import CommunityCommentSummaryDTO
from app.modules.community_comments.public.interfaces import CommentQueryPort


class CommentFacade(CommentQueryPort):
    def __init__(self, *, comment_repository: CommunityCommentRepository) -> None:
        self._comments = comment_repository

    async def comment_exists(self, comment_id: UUID) -> bool:
        return await self._comments.get_by_id(comment_id) is not None

    async def get_comment_summary(self, comment_id: UUID) -> CommunityCommentSummaryDTO | None:
        comment = await self._comments.get_by_id(comment_id)
        return comment_to_summary(comment) if comment is not None else None

    async def get_thread_summaries(self, root_comment_id: UUID) -> list[CommunityCommentSummaryDTO]:
        comments = await self._comments.get_thread(root_comment_id, max_depth=MAX_COMMENT_DEPTH)
        return [comment_to_summary(c) for c in comments]
