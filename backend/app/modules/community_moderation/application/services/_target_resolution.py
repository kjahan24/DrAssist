"""Resolves a `(ModerationTargetType, target_id)` pair to the information
every caller in this module actually needs: which organization it belongs
to (for tenant isolation) and, where the target has one, which community
it belongs to (for `CommunityRole`-based moderator authorization).

One resolver for all six target types, reusing each peer module's own
already-public, read-only query port — the same "no per-content-type
duplication" shape `app.modules.community_engagement.application.services
._target_resolution.resolve_engagement_target` already establishes,
extended with `COMMUNITY` (via `CommunityQueryPort` itself) and `USER`
(via `UserQueryPort`, which has no inherent community — `community_id`
resolves to `None` for that one case; the caller supplies and separately
validates its own community context — see `CreateReportService`'s own
docstring for why).

Cross-tenant existence collapses into "not found," never a distinct
error — the same deliberate anti-enumeration posture
`app.modules.community_comments.application.services._target_resolution
.resolve_target_for_new_comment`'s own docstring establishes: a caller
must never be able to distinguish "this id doesn't exist" from "it exists,
in someone else's organization." Comparing the returned `organization_id`
against the caller's own is each service's own responsibility, not this
resolver's — mirroring the identical split in every prior phase's own
target resolver.
"""

from dataclasses import dataclass
from uuid import UUID

from app.modules.authentication.public.interfaces import UserQueryPort
from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_answers.public.interfaces import AnswerQueryPort
from app.modules.community_comments.public.interfaces import CommentQueryPort
from app.modules.community_moderation.domain.enums import ModerationTargetType
from app.modules.community_posts.public.interfaces import PostQueryPort
from app.modules.community_questions.public.interfaces import QuestionQueryPort


@dataclass(frozen=True, slots=True)
class ResolvedModerationTarget:
    organization_id: UUID
    community_id: UUID | None


async def resolve_moderation_target(
    target_type: ModerationTargetType,
    target_id: UUID,
    *,
    post_query_port: PostQueryPort,
    question_query_port: QuestionQueryPort,
    answer_query_port: AnswerQueryPort,
    comment_query_port: CommentQueryPort,
    community_query_port: CommunityQueryPort,
    user_query_port: UserQueryPort,
) -> ResolvedModerationTarget | None:
    if target_type is ModerationTargetType.POST:
        post = await post_query_port.get_post_summary(target_id)
        if post is None:
            return None
        return ResolvedModerationTarget(
            organization_id=post.organization_id, community_id=post.community_id
        )
    if target_type is ModerationTargetType.QUESTION:
        question = await question_query_port.get_question_summary(target_id)
        if question is None:
            return None
        return ResolvedModerationTarget(
            organization_id=question.organization_id, community_id=question.community_id
        )
    if target_type is ModerationTargetType.ANSWER:
        answer = await answer_query_port.get_answer_summary(target_id)
        if answer is None:
            return None
        return ResolvedModerationTarget(
            organization_id=answer.organization_id, community_id=answer.community_id
        )
    if target_type is ModerationTargetType.COMMENT:
        comment = await comment_query_port.get_comment_summary(target_id)
        if comment is None:
            return None
        return ResolvedModerationTarget(
            organization_id=comment.organization_id, community_id=comment.community_id
        )
    if target_type is ModerationTargetType.COMMUNITY:
        community = await community_query_port.get_community_summary(target_id)
        if community is None:
            return None
        return ResolvedModerationTarget(
            organization_id=community.organization_id, community_id=community.community_id
        )
    # ModerationTargetType.USER — no inherent community; the caller
    # supplies and separately validates its own community context.
    user = await user_query_port.get_user_summary(target_id)
    if user is None:
        return None
    return ResolvedModerationTarget(organization_id=user.organization_id, community_id=None)
