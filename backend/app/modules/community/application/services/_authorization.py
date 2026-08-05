"""Role-hierarchy authorization helper shared by every mutating Community
service — intra-module only (not `app.shared`, since this is specific to
`CommunityRole`'s own ranking), the same "small intra-module helper"
scope `app.modules.risk_stratification_ai.application.services._dedupe
.dedupe_preserving_order` establishes for its own, analogous need.

There is no RBAC `require_permission` integration here: `app.api.deps
.require_permission` checks a *global* permission code against the
caller's organization-wide roles, but community moderation is a
*per-community* concept (the same user can be an `OWNER` of one
community and a plain `MEMBER` of another) — a global permission code
cannot express that, so authorization is enforced here instead, against
the caller's own `CommunityMember` row for the specific community being
acted on.
"""

from uuid import UUID

from app.modules.community.domain.entities import CommunityMember
from app.modules.community.domain.enums import CommunityMemberStatus, CommunityRole
from app.modules.community.domain.exceptions import (
    CommunityMembershipNotFoundError,
    InsufficientCommunityRoleError,
)

_ROLE_RANK: dict[CommunityRole, int] = {
    CommunityRole.MEMBER: 0,
    CommunityRole.MODERATOR: 1,
    CommunityRole.ADMIN: 2,
    CommunityRole.OWNER: 3,
}


def ensure_role_at_least(
    member: CommunityMember | None,
    minimum_role: CommunityRole,
    *,
    community_id: UUID,
    user_id: UUID,
) -> None:
    """Raises `CommunityMembershipNotFoundError` if the caller has no
    active membership at all, otherwise `InsufficientCommunityRoleError`
    if their role ranks below `minimum_role`."""
    if member is None or member.status is not CommunityMemberStatus.ACTIVE:
        raise CommunityMembershipNotFoundError(community_id, user_id)
    if _ROLE_RANK[member.role] < _ROLE_RANK[minimum_role]:
        raise InsufficientCommunityRoleError(community_id, user_id, minimum_role.value)
