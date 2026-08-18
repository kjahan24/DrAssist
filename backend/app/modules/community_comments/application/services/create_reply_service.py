"""`CreateReplyService` — provisions a new `CommunityComment` nested
under an existing parent comment (itself a top-level comment or another
reply, at any depth). See `create_comment_service.CreateCommentService`
for the top-level case.

Never resolves a Post/Question/Answer target itself: `parent_comment_id`
is looked up directly via `CommunityCommentRepository.get_by_id`, and
`CommunityComment.create_reply` copies every target/tenant field straight
off that loaded parent — see that classmethod's own docstring for why
this is what makes "no ambiguous or conflicting target ownership"
structurally guaranteed for a reply.

Enforces, in order: "Author must be authorized" (`ensure_can_create` —
any active community member of the parent's own community), the parent
must exist (`ParentCommentNotFoundError`), the parent must currently be
`PUBLISHED` (`ParentCommentNotAcceptingRepliesError` — this task's own
"Deleted/archived parent handling": a dead parent accepts no *new*
replies, though its existing ones are left untouched, see
`CommunityComment.archive`/`.delete`'s own docstrings), and the maximum
safe nesting depth (`MaxCommentDepthExceededError`, enforced by
`CommunityComment.create_reply` itself). There is no separate
"can the caller view the parent" check the way `CreateCommentService`
checks target visibility — a `PUBLISHED` comment is visible to any
caller who can reach this module's API at all, see
`_authorization.ensure_can_view`'s own docstring.
"""

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_comments.application.dto import CreateReplyInput, CreateReplyOutput
from app.modules.community_comments.application.services._authorization import ensure_can_create
from app.modules.community_comments.domain.entities import CommunityComment
from app.modules.community_comments.domain.enums import CommentStatus
from app.modules.community_comments.domain.exceptions import (
    ParentCommentNotAcceptingRepliesError,
    ParentCommentNotFoundError,
)
from app.modules.community_comments.domain.repositories import CommunityCommentRepository
from app.modules.community_comments.domain.value_objects import CommentBody
from app.shared.application.unit_of_work import UnitOfWork


class CreateReplyService:
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

    async def execute(self, input_dto: CreateReplyInput) -> CreateReplyOutput:
        parent = await self._comments.get_by_id(input_dto.parent_comment_id)
        if parent is None:
            raise ParentCommentNotFoundError(input_dto.parent_comment_id)
        if parent.status is not CommentStatus.PUBLISHED:
            raise ParentCommentNotAcceptingRepliesError(input_dto.parent_comment_id)

        member = await self._communities.get_membership(parent.community_id, input_dto.author_id)
        ensure_can_create(member, community_id=parent.community_id, user_id=input_dto.author_id)

        reply = CommunityComment.create_reply(
            parent=parent,
            author_id=input_dto.author_id,
            body=CommentBody(input_dto.body),
            is_anonymous=input_dto.is_anonymous,
        )
        await self._comments.add(reply)
        self._uow.collect_events(reply.pull_events())
        await self._uow.commit()

        return CreateReplyOutput(
            comment_id=reply.id,
            parent_comment_id=input_dto.parent_comment_id,
            root_comment_id=reply.root_comment_id,
            depth=reply.depth,
            status=reply.status,
        )
