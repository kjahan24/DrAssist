"""`ListCommentsService` — every published, *top-level* comment
(`parent_comment_id IS NULL`) for one target (Post/Question/Answer),
cursor-paginated, newest-or-oldest ordered. Named "List" (matching this
task's own APPLICATION section literally) rather than "Browse" (the
naming `app.modules.community_posts`/`app.modules.community_questions`
use for their own cursor-paginated feeds) — the underlying pagination
*is* cursor-based regardless, per this task's own QUERY/PAGINATION
section: "Use deterministic cursor pagination." Delegates to
`CommunityCommentRepository.browse` with `top_level_only=True` — see
that method's own docstring for why one flexible method backs every
listing/searching service in this module."""

from app.modules.community_comments.application.dto import CommentFeedOutput, ListCommentsInput
from app.modules.community_comments.application.services._summary_mappers import (
    comment_to_summary,
)
from app.modules.community_comments.domain.enums import CommentStatus
from app.modules.community_comments.domain.repositories import CommunityCommentRepository


class ListCommentsService:
    def __init__(self, *, comment_repository: CommunityCommentRepository) -> None:
        self._comments = comment_repository

    async def list_comments(self, input_dto: ListCommentsInput) -> CommentFeedOutput:
        comments, next_cursor = await self._comments.browse(
            organization_id=input_dto.organization_id,
            target_type=input_dto.target_type,
            target_id=input_dto.target_id,
            top_level_only=True,
            status=input_dto.status or (CommentStatus.PUBLISHED,),
            sort_order=input_dto.sort_order,
            cursor=input_dto.cursor,
            limit=input_dto.limit,
        )
        return CommentFeedOutput(
            items=tuple(comment_to_summary(c) for c in comments), next_cursor=next_cursor
        )
