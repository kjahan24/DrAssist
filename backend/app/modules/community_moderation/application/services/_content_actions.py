"""Shared resolve+authorize+"current state" helpers for every
content-shaped moderation action (`CreateModerationAction` when given a
content-shaped `action_type`, `ReviewContent`, `RemoveContent`,
`RestoreContent`, `LockContent`) — factored out once so those five
services share one target-resolution/authorization/state-lookup
implementation rather than five near-identical copies, directly
satisfying this task's own "Use polymorphic target/reference handling
without duplicating moderation logic" DOMAIN requirement.
"""

from uuid import UUID

from app.modules.authentication.public.interfaces import UserQueryPort
from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_answers.public.interfaces import AnswerQueryPort
from app.modules.community_comments.public.interfaces import CommentQueryPort
from app.modules.community_moderation.application.services._authorization import (
    ensure_is_moderator,
)
from app.modules.community_moderation.application.services._target_resolution import (
    resolve_moderation_target,
)
from app.modules.community_moderation.domain.enums import (
    ContentModerationStatus,
    ModerationTargetType,
)
from app.modules.community_moderation.domain.exceptions import (
    ContentActionTargetNotFoundError,
    UnsupportedModerationTargetTypeError,
)
from app.modules.community_moderation.domain.repositories import ModerationActionRepository
from app.modules.community_posts.public.interfaces import PostQueryPort
from app.modules.community_questions.public.interfaces import QuestionQueryPort

CONTENT_TARGET_TYPES = frozenset(
    {
        ModerationTargetType.POST,
        ModerationTargetType.QUESTION,
        ModerationTargetType.ANSWER,
        ModerationTargetType.COMMENT,
    }
)


async def resolve_and_authorize_content_target(
    target_type: ModerationTargetType,
    target_id: UUID,
    *,
    organization_id: UUID,
    actor_id: UUID,
    post_query_port: PostQueryPort,
    question_query_port: QuestionQueryPort,
    answer_query_port: AnswerQueryPort,
    comment_query_port: CommentQueryPort,
    community_query_port: CommunityQueryPort,
    user_query_port: UserQueryPort,
) -> UUID:
    """Returns the target's own `community_id` once the target is
    confirmed to exist, belong to `organization_id`, and `actor_id` is
    confirmed to hold `MODERATOR`-or-above rank in that community."""
    if target_type not in CONTENT_TARGET_TYPES:
        raise UnsupportedModerationTargetTypeError(target_type)

    resolved = await resolve_moderation_target(
        target_type,
        target_id,
        post_query_port=post_query_port,
        question_query_port=question_query_port,
        answer_query_port=answer_query_port,
        comment_query_port=comment_query_port,
        community_query_port=community_query_port,
        user_query_port=user_query_port,
    )
    if (
        resolved is None
        or resolved.organization_id != organization_id
        or resolved.community_id is None
    ):
        raise ContentActionTargetNotFoundError(target_id)

    member = await community_query_port.get_membership(resolved.community_id, actor_id)
    ensure_is_moderator(member, community_id=resolved.community_id, user_id=actor_id)
    return resolved.community_id


async def get_current_content_status(
    action_repository: ModerationActionRepository,
    target_type: ModerationTargetType,
    target_id: UUID,
) -> ContentModerationStatus:
    """The current moderation status of a content target, computed live —
    see `ModerationAction`'s own module docstring for why."""
    latest = await action_repository.get_latest_for_target(target_type, target_id)
    if latest is None or latest.new_state is None:
        return ContentModerationStatus.ACTIVE
    return ContentModerationStatus(latest.new_state)
