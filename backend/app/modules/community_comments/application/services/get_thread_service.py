"""`GetThreadService` — the entire bounded-depth conversation rooted at
one comment (the root itself plus every descendant reply, up to
`max_depth`), fetched with a single flat, non-recursive query — see
`CommunityCommentRepository.get_thread`'s own docstring for the full
"Do not use unbounded recursive queries" / "Use safe bounded-depth
thread retrieval" reasoning.

Returns a flat `ThreadOutput` (ordered `(depth, created_at)` ascending,
matching the repository's own ordering) rather than a nested tree
structure — reconstructing the visual tree shape from each item's own
`parent_comment_id` is a presentation-layer concern, not an application
one; building a recursive DTO here would duplicate work the client
already has to do to *render* the tree anyway.
"""

from uuid import UUID

from app.modules.community_comments.application.dto import ThreadOutput
from app.modules.community_comments.application.services._summary_mappers import (
    comment_to_summary,
)
from app.modules.community_comments.domain.entities import MAX_COMMENT_DEPTH
from app.modules.community_comments.domain.enums import CommentStatus
from app.modules.community_comments.domain.repositories import CommunityCommentRepository


class GetThreadService:
    def __init__(self, *, comment_repository: CommunityCommentRepository) -> None:
        self._comments = comment_repository

    async def get_thread(
        self, root_comment_id: UUID, *, max_depth: int = MAX_COMMENT_DEPTH
    ) -> ThreadOutput:
        items = await self._comments.get_thread(
            root_comment_id, max_depth=max_depth, status=(CommentStatus.PUBLISHED,)
        )
        return ThreadOutput(items=tuple(comment_to_summary(c) for c in items))
