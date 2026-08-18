"""Resolves a `CommentTargetType` + target id into the information a new
*top-level* comment needs to be created against it — used only by
`CreateCommentService`. `CreateReplyService` never calls this: a reply's
target is always copied straight off its already-loaded parent
`CommunityComment` row, never re-resolved — see that service's own
docstring.

Existence and "open to new comments" (`PUBLISHED`) validation happens
here, once, via the appropriate peer module's own public query port
(`PostQueryPort`/`QuestionQueryPort`/`AnswerQueryPort`) — the same
"cross-module reads only, never a private repository import" rule
`app.modules.community_answers.application.services.create_answer_service
.CreateAnswerService` already follows for its own `question_id`
resolution.

Status/visibility are compared by their raw `.value` string
(`"published"`/`"public"`/`"members_only"`/`"private"`) rather than by
importing `PostStatus`/`QuestionStatus`/`AnswerStatus`/`PostVisibility`/
`QuestionVisibility`/`AnswerVisibility` from three different peer
modules — every one of those `StrEnum`s already shares these exact
string values by convention, so comparing on `.value` gets the same
correctness with a third of the imports and no per-target-type branching
duplicated at every call site that needs it.
"""

from dataclasses import dataclass
from uuid import UUID

from app.modules.community_answers.public.interfaces import AnswerQueryPort
from app.modules.community_comments.domain.enums import CommentTargetType
from app.modules.community_comments.domain.exceptions import (
    TargetNotAcceptingCommentsError,
    TargetNotFoundForCommentError,
)
from app.modules.community_posts.public.interfaces import PostQueryPort
from app.modules.community_questions.public.interfaces import QuestionQueryPort

_PUBLISHED = "published"


@dataclass(frozen=True, slots=True)
class ResolvedTarget:
    """`author_id` is `None` when the target itself is anonymous —
    `CommunityAnswerSummaryDTO.author_id` is masked unconditionally, even
    for this module-to-module read (see `app.modules.community_answers
    .application.services._summary_mappers.answer_to_summary`'s own
    docstring). `_authorization.ensure_can_view_target` treats a `None`
    author here as "the true author cannot be confirmed," falling
    through to the moderator-only branch for a `PRIVATE` target rather
    than ever silently granting access."""

    community_id: UUID
    organization_id: UUID
    visibility_value: str
    author_id: UUID | None = None
    topic_id: UUID | None = None


async def resolve_target_for_new_comment(
    target_type: CommentTargetType,
    target_id: UUID,
    *,
    post_query_port: PostQueryPort,
    question_query_port: QuestionQueryPort,
    answer_query_port: AnswerQueryPort,
) -> ResolvedTarget:
    if target_type is CommentTargetType.POST:
        post = await post_query_port.get_post_summary(target_id)
        if post is None:
            raise TargetNotFoundForCommentError(target_id)
        if post.status.value != _PUBLISHED:
            raise TargetNotAcceptingCommentsError(target_id)
        return ResolvedTarget(
            community_id=post.community_id,
            organization_id=post.organization_id,
            author_id=post.author_id,
            visibility_value=post.visibility.value,
            topic_id=None,
        )

    if target_type is CommentTargetType.QUESTION:
        question = await question_query_port.get_question_summary(target_id)
        if question is None:
            raise TargetNotFoundForCommentError(target_id)
        if question.status.value != _PUBLISHED:
            raise TargetNotAcceptingCommentsError(target_id)
        return ResolvedTarget(
            community_id=question.community_id,
            organization_id=question.organization_id,
            author_id=question.author_id,
            visibility_value=question.visibility.value,
            topic_id=question.primary_topic_id,
        )

    answer = await answer_query_port.get_answer_summary(target_id)
    if answer is None:
        raise TargetNotFoundForCommentError(target_id)
    if answer.status.value != _PUBLISHED:
        raise TargetNotAcceptingCommentsError(target_id)
    return ResolvedTarget(
        community_id=answer.community_id,
        organization_id=answer.organization_id,
        author_id=answer.author_id,
        visibility_value=answer.visibility.value,
        topic_id=answer.topic_id,
    )
