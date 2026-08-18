"""`ArchiveCommentService` — author-or-moderator authorized, the same
rule `UpdateCommentService` uses. Used uniformly for both top-level
comments and replies. Never cascades to this comment's own replies — see
`CommunityComment.archive`'s own docstring."""

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_comments.application.dto import (
    ArchiveCommentInput,
    CommunityCommentSummaryDTO,
)
from app.modules.community_comments.application.services._authorization import (
    ensure_can_author_action,
)
from app.modules.community_comments.application.services._summary_mappers import (
    comment_to_summary,
)
from app.modules.community_comments.domain.exceptions import CommentNotFoundError
from app.modules.community_comments.domain.repositories import CommunityCommentRepository
from app.shared.application.unit_of_work import UnitOfWork


class ArchiveCommentService:
    def __init__(
        self,
        *,
        comment_repository: CommunityCommentRepository,
        community_query_port: CommunityQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._comments = comment_repository
        self._communities = community_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: ArchiveCommentInput) -> CommunityCommentSummaryDTO:
        comment = await self._comments.get_by_id(input_dto.comment_id)
        if comment is None:
            raise CommentNotFoundError(input_dto.comment_id)

        member = await self._communities.get_membership(
            comment.community_id, input_dto.acting_user_id
        )
        ensure_can_author_action(
            member,
            community_id=comment.community_id,
            user_id=input_dto.acting_user_id,
            author_id=comment.author_id,
        )

        comment.archive()
        await self._comments.add(comment)
        self._uow.collect_events(comment.pull_events())
        await self._uow.commit()

        return comment_to_summary(comment)
