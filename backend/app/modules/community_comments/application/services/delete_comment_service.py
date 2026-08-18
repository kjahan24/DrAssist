"""`DeleteCommentService` — the author (or a community moderator/admin)
may delete their own comment or reply, the same authorization rule
`UpdateCommentService` uses.

Deletion here is a domain-level status transition
(`CommunityComment.delete()`), persisted through the ordinary `add()`
upsert — see `CommentStatus`'s own docstring for why. Never cascades to
this comment's own replies — see `CommunityComment.delete`'s own
docstring."""

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_comments.application.dto import DeleteCommentInput
from app.modules.community_comments.application.services._authorization import (
    ensure_can_author_action,
)
from app.modules.community_comments.domain.exceptions import CommentNotFoundError
from app.modules.community_comments.domain.repositories import CommunityCommentRepository
from app.shared.application.unit_of_work import UnitOfWork


class DeleteCommentService:
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

    async def execute(self, input_dto: DeleteCommentInput) -> None:
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

        comment.delete()
        await self._comments.add(comment)
        self._uow.collect_events(comment.pull_events())
        await self._uow.commit()
