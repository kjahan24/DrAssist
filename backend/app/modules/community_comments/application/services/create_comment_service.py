"""`CreateCommentService` — provisions a new, *top-level*
`CommunityComment` against an existing, published Post/Question/Answer.
See `create_reply_service.CreateReplyService` for the nested case.

Cross-module reads only, never a private repository import:
`_target_resolution.resolve_target_for_new_comment` resolves the
target's own `community_id`/`organization_id`/`topic_id`/`author_id`/
`visibility` (denormalized onto the new comment — see `CommunityComment`'s
own module docstring) and validates the target is actually open to new
comments; `CommunityQueryPort.get_membership` validates the acting
author's community membership.

Enforces, in order, this task's own DOMAIN section requirements: "A
comment/reply must belong to exactly one supported target"
(`target_type`/`target_id` are the input's own required fields — there is
no way to construct an ambiguous target through this DTO),
"Author must be authorized" (`ensure_can_create` — any active community
member), plus this module's own additional guard that a target not
currently published cannot receive new comments, and that the acting
user must actually be able to *see* the target before commenting on it
(`ensure_can_view_target`).
"""

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_answers.public.interfaces import AnswerQueryPort
from app.modules.community_comments.application.dto import CreateCommentInput, CreateCommentOutput
from app.modules.community_comments.application.services._authorization import (
    ensure_can_create,
    ensure_can_view_target,
)
from app.modules.community_comments.application.services._target_resolution import (
    resolve_target_for_new_comment,
)
from app.modules.community_comments.domain.entities import CommunityComment
from app.modules.community_comments.domain.repositories import CommunityCommentRepository
from app.modules.community_comments.domain.value_objects import CommentBody
from app.modules.community_posts.public.interfaces import PostQueryPort
from app.modules.community_questions.public.interfaces import QuestionQueryPort
from app.shared.application.unit_of_work import UnitOfWork


class CreateCommentService:
    def __init__(
        self,
        *,
        comment_repository: CommunityCommentRepository,
        community_query_port: CommunityQueryPort,
        post_query_port: PostQueryPort,
        question_query_port: QuestionQueryPort,
        answer_query_port: AnswerQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._comments = comment_repository
        self._communities = community_query_port
        self._posts = post_query_port
        self._questions = question_query_port
        self._answers = answer_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: CreateCommentInput) -> CreateCommentOutput:
        target = await resolve_target_for_new_comment(
            input_dto.target_type,
            input_dto.target_id,
            post_query_port=self._posts,
            question_query_port=self._questions,
            answer_query_port=self._answers,
        )

        member = await self._communities.get_membership(target.community_id, input_dto.author_id)
        ensure_can_create(member, community_id=target.community_id, user_id=input_dto.author_id)
        ensure_can_view_target(
            target_id=input_dto.target_id,
            visibility_value=target.visibility_value,
            target_author_id=target.author_id,
            member=member,
            user_id=input_dto.author_id,
        )

        comment = CommunityComment.create(
            target_type=input_dto.target_type,
            target_id=input_dto.target_id,
            community_id=target.community_id,
            organization_id=target.organization_id,
            topic_id=target.topic_id,
            author_id=input_dto.author_id,
            body=CommentBody(input_dto.body),
            is_anonymous=input_dto.is_anonymous,
        )
        await self._comments.add(comment)
        self._uow.collect_events(comment.pull_events())
        await self._uow.commit()

        return CreateCommentOutput(
            comment_id=comment.id,
            target_type=comment.target_type,
            target_id=comment.target_id,
            status=comment.status,
        )
