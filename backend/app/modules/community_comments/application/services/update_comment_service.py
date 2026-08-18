"""`UpdateCommentService` — the author (or a community moderator/admin)
may edit a comment's own content — see
`_authorization.ensure_can_author_action` for the exact rule. Used
uniformly for both top-level comments and replies (any depth) — see
`CommunityComment`'s own module docstring for why there is no separate
`UpdateReplyService`.

Persists the `CommunityCommentRevision` `CommunityComment.update_content`
may return, in the same transaction as the comment's own update — see
that method's own docstring for when a revision is (and isn't) created.
"""

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_comments.application.dto import UpdateCommentInput, UpdateCommentOutput
from app.modules.community_comments.application.services._authorization import (
    ensure_can_author_action,
)
from app.modules.community_comments.domain.exceptions import CommentNotFoundError
from app.modules.community_comments.domain.repositories import (
    CommunityCommentRepository,
    CommunityCommentRevisionRepository,
)
from app.modules.community_comments.domain.value_objects import CommentBody
from app.shared.application.unit_of_work import UnitOfWork


class UpdateCommentService:
    def __init__(
        self,
        *,
        comment_repository: CommunityCommentRepository,
        comment_revision_repository: CommunityCommentRevisionRepository,
        community_query_port: CommunityQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._comments = comment_repository
        self._revisions = comment_revision_repository
        self._communities = community_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: UpdateCommentInput) -> UpdateCommentOutput:
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

        revision = comment.update_content(
            body=CommentBody(input_dto.body) if input_dto.body is not None else None,
            updated_by=input_dto.acting_user_id,
        )

        await self._comments.add(comment)
        events = list(comment.pull_events())
        if revision is not None:
            await self._revisions.add(revision)
            events.extend(revision.pull_events())

        self._uow.collect_events(events)
        await self._uow.commit()

        return UpdateCommentOutput(
            comment_id=comment.id, status=comment.status, revision_number=comment.revision_number
        )
