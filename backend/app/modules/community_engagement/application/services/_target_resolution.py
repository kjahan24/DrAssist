"""Resolves an `EngagementTargetType` + target id into the information
`CastVoteService`/`SaveContentService` need to validate it — one shared
resolver for both use cases (this task's own "Do not duplicate voting
logic for every content type" instruction, extended here to saving too,
since the two share the exact same four-way target lookup).

Existence and tenant ownership validation happens here, once, via the
appropriate peer module's own public query port (`PostQueryPort`/
`QuestionQueryPort`/`AnswerQueryPort`/`CommentQueryPort`) — the same
"cross-module reads only, never a private repository import" rule
`app.modules.community_comments.application.services._target_resolution`
already establishes for itself, extended here to a fourth target type.

Status is compared by its raw `.value` string (`"published"`) rather
than by importing `PostStatus`/`QuestionStatus`/`AnswerStatus`/
`CommentStatus` from four different peer modules — see that module's own
docstring for why comparing on `.value` is preferred over importing four
enums just to compare identity.

This function deliberately returns `None` for "not found" rather than
raising — `VoteTargetNotFoundError`/`SaveTargetNotFoundError` are two
different exception types for what is, from this resolver's own
perspective, the identical situation, so the two calling services each
decide which one to raise themselves; see their own docstrings for why
"belongs to a different organization" also collapses onto this same
`None` result (this task's own "Tenant isolation" DOMAIN rule — the
caller compares `organization_id` against the acting user's own and
treats a mismatch exactly like a missing target, the same
never-distinguish-cross-tenant-existence reasoning
`app.modules.community_comments.domain.exceptions
.TargetNotFoundForCommentError`'s own docstring already establishes for
the Comments module).
"""

from dataclasses import dataclass
from uuid import UUID

from app.modules.community_answers.public.interfaces import AnswerQueryPort
from app.modules.community_comments.public.interfaces import CommentQueryPort
from app.modules.community_engagement.domain.enums import EngagementTargetType
from app.modules.community_posts.public.interfaces import PostQueryPort
from app.modules.community_questions.public.interfaces import QuestionQueryPort

_PUBLISHED = "published"


@dataclass(frozen=True, slots=True)
class ResolvedEngagementTarget:
    organization_id: UUID
    is_published: bool


async def resolve_engagement_target(
    target_type: EngagementTargetType,
    target_id: UUID,
    *,
    post_query_port: PostQueryPort,
    question_query_port: QuestionQueryPort,
    answer_query_port: AnswerQueryPort,
    comment_query_port: CommentQueryPort,
) -> ResolvedEngagementTarget | None:
    if target_type is EngagementTargetType.POST:
        post = await post_query_port.get_post_summary(target_id)
        if post is None:
            return None
        return ResolvedEngagementTarget(
            organization_id=post.organization_id, is_published=post.status.value == _PUBLISHED
        )

    if target_type is EngagementTargetType.QUESTION:
        question = await question_query_port.get_question_summary(target_id)
        if question is None:
            return None
        return ResolvedEngagementTarget(
            organization_id=question.organization_id,
            is_published=question.status.value == _PUBLISHED,
        )

    if target_type is EngagementTargetType.ANSWER:
        answer = await answer_query_port.get_answer_summary(target_id)
        if answer is None:
            return None
        return ResolvedEngagementTarget(
            organization_id=answer.organization_id, is_published=answer.status.value == _PUBLISHED
        )

    comment = await comment_query_port.get_comment_summary(target_id)
    if comment is None:
        return None
    return ResolvedEngagementTarget(
        organization_id=comment.organization_id, is_published=comment.status.value == _PUBLISHED
    )
