"""Authorization helpers for the Community Moderation module.

`_ROLE_RANK`/`ensure_is_moderator`/`ensure_is_admin` reuse the exact
`CommunityRole` rank hierarchy every content module's own
`application/services/_authorization.py` already established (see e.g.
`app.modules.community_posts.application.services._authorization
.ensure_is_moderator`) — kept as a local copy rather than an import, since
each module's own `_authorization.py` is private to that module (never
part of any `public/` surface) and this module has its own distinct
exception types (`InsufficientModeratorRoleError`, not
`InsufficientPostRoleError`) to raise.

`ensure_is_admin` is new relative to every prior module's identical file
— nothing before this task needed a rank stricter than `MODERATOR`. It
backs "Permanent ban where authorized": a time-bounded suspension only
needs `MODERATOR`-or-above, but a `PERMANENT_BAN` needs `ADMIN`-or-above,
per `SuspendUserService`'s own docstring.
"""

from uuid import UUID

from app.modules.community.public.dto import (
    CommunityMemberStatus,
    CommunityMemberSummaryDTO,
    CommunityRole,
)
from app.modules.community_moderation.domain.exceptions import (
    InsufficientAdminRoleError,
    InsufficientModeratorRoleError,
    ModerationMembershipRequiredError,
)

_ROLE_RANK: dict[CommunityRole, int] = {
    CommunityRole.MEMBER: 0,
    CommunityRole.MODERATOR: 1,
    CommunityRole.ADMIN: 2,
    CommunityRole.OWNER: 3,
}


def _ensure_active_member(
    member: CommunityMemberSummaryDTO | None, *, community_id: UUID, user_id: UUID
) -> CommunityMemberSummaryDTO:
    if member is None or member.status is not CommunityMemberStatus.ACTIVE:
        raise ModerationMembershipRequiredError(community_id, user_id)
    return member


def ensure_can_create(
    member: CommunityMemberSummaryDTO | None, *, community_id: UUID, user_id: UUID
) -> None:
    _ensure_active_member(member, community_id=community_id, user_id=user_id)


def ensure_is_moderator(
    member: CommunityMemberSummaryDTO | None, *, community_id: UUID, user_id: UUID
) -> None:
    active_member = _ensure_active_member(member, community_id=community_id, user_id=user_id)
    if _ROLE_RANK[active_member.role] < _ROLE_RANK[CommunityRole.MODERATOR]:
        raise InsufficientModeratorRoleError(community_id, user_id)


def ensure_is_admin(
    member: CommunityMemberSummaryDTO | None, *, community_id: UUID, user_id: UUID
) -> None:
    active_member = _ensure_active_member(member, community_id=community_id, user_id=user_id)
    if _ROLE_RANK[active_member.role] < _ROLE_RANK[CommunityRole.ADMIN]:
        raise InsufficientAdminRoleError(community_id, user_id)
