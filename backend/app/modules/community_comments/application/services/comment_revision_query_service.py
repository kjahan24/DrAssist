"""`CommentRevisionQueryService` — read-only access to a comment's own
revision history (this task's own REVISION HISTORY section). No
create/remove methods here: revisions are created automatically, as a
side effect of `CommunityComment.update_content`, persisted by
`UpdateCommentService` — see those two's own docstrings. There is
deliberately no `CommunityCommentRevisionRepository.remove` for this
service to ever call — see that repository's own docstring: revision
history is immutable, full stop.
"""

from uuid import UUID

from app.modules.community_comments.application.dto import CommentRevisionSummaryDTO
from app.modules.community_comments.application.services._summary_mappers import (
    comment_revision_to_summary,
)
from app.modules.community_comments.domain.repositories import CommunityCommentRevisionRepository


class CommentRevisionQueryService:
    def __init__(self, *, comment_revision_repository: CommunityCommentRevisionRepository) -> None:
        self._revisions = comment_revision_repository

    async def list_revisions(
        self, comment_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[CommentRevisionSummaryDTO]:
        revisions = await self._revisions.list_by_comment(comment_id, offset=offset, limit=limit)
        return [comment_revision_to_summary(r) for r in revisions]
