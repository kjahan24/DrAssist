"""Shared resolve+authorize helper for `WarnUserService`/
`RestrictUserService`/`SuspendUserService` — factored out once so all
three share one target-validation/self-moderation/authorization
implementation, mirroring `_content_actions.py`'s identical role for the
four content-shaped services.
"""

from uuid import UUID

from app.modules.authentication.public.interfaces import UserQueryPort
from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_moderation.application.services._authorization import (
    ensure_is_admin,
    ensure_is_moderator,
)
from app.modules.community_moderation.domain.exceptions import (
    CannotModerateSelfError,
    UserNotFoundForModerationError,
)


async def resolve_and_authorize_user_restriction(
    *,
    organization_id: UUID,
    community_id: UUID,
    moderator_id: UUID,
    user_id: UUID,
    community_query_port: CommunityQueryPort,
    user_query_port: UserQueryPort,
    require_admin: bool = False,
) -> None:
    if moderator_id == user_id:
        raise CannotModerateSelfError(user_id)

    target_user = await user_query_port.get_user_summary(user_id)
    if target_user is None or target_user.organization_id != organization_id:
        raise UserNotFoundForModerationError(user_id)

    member = await community_query_port.get_membership(community_id, moderator_id)
    if require_admin:
        ensure_is_admin(member, community_id=community_id, user_id=moderator_id)
    else:
        ensure_is_moderator(member, community_id=community_id, user_id=moderator_id)
