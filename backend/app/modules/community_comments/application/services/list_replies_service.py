"""`ListRepliesService` — every published, *direct* reply of one parent
comment, cursor-paginated. Distinct from `get_thread_service
.GetThreadService`: this is one level of nesting (`parent_comment_id ==
X`), the natural shape for a "load more replies" UI action; `GetThread`
is the full bounded-depth subtree from a root, fetched flat in one shot
— see that service's own docstring."""

from app.modules.community_comments.application.dto import CommentFeedOutput, ListRepliesInput
from app.modules.community_comments.application.services._summary_mappers import (
    comment_to_summary,
)
from app.modules.community_comments.domain.enums import CommentStatus
from app.modules.community_comments.domain.repositories import CommunityCommentRepository


class ListRepliesService:
    def __init__(self, *, comment_repository: CommunityCommentRepository) -> None:
        self._comments = comment_repository

    async def list_replies(self, input_dto: ListRepliesInput) -> CommentFeedOutput:
        replies, next_cursor = await self._comments.browse(
            organization_id=input_dto.organization_id,
            parent_comment_id=input_dto.parent_comment_id,
            status=input_dto.status or (CommentStatus.PUBLISHED,),
            sort_order=input_dto.sort_order,
            cursor=input_dto.cursor,
            limit=input_dto.limit,
        )
        return CommentFeedOutput(
            items=tuple(comment_to_summary(c) for c in replies), next_cursor=next_cursor
        )
