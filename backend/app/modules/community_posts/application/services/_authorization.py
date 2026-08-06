"""Role-hierarchy authorization helpers shared by every mutating Community
Posts service.

Unlike `app.modules.community.application.services._authorization
.ensure_role_at_least` (which checks a `CommunityMember` *domain entity*
this module has no direct database access to), these helpers operate on
`CommunityMemberSummaryDTO` — the read model returned by
`app.modules.community.public.interfaces.CommunityQueryPort
.get_membership`, this module's only allowed way to know anything about
Community membership (see `docs/backend-architecture/10_module_communication
.md` — modules communicate through public ports only, never by reaching
into another module's private repositories). This is the first real
consumer of `CommunityQueryPort` — see that port's own docstring, which
named this exact module as an expected future dependent.

Authorization split, matching this task's own FEATURES/APPLICATION
sections:
- `ensure_can_author_action` (Update/Delete/Publish/Archive): the acting
  user must be either the post's own author, or hold at least `MODERATOR`
  in the post's community — an author manages their own content; a
  moderator manages anyone's.
- `ensure_is_moderator` (Pin/Lock/Feature): moderator-only, no author
  exception — pinning/locking/featuring a post is always a moderation
  action in this module's own design, never something an author does to
  their own post (see `CommunityPost.set_pinned`'s own docstring).
- `ensure_can_create` (Create): any active community member may submit a
  post — the same "any member, no special role" bar
  `app.modules.community.application.services.create_community_service`
  sets for creating a community's own posts-equivalent action, joining.
- `ensure_can_view` (Get): enforces `PostVisibility` — see that enum's
  own docstring for the three tiers.
"""

from uuid import UUID

from app.modules.community.public.dto import (
    CommunityMemberStatus,
    CommunityMemberSummaryDTO,
    CommunityRole,
)
from app.modules.community_posts.domain.entities import CommunityPost
from app.modules.community_posts.domain.enums import PostVisibility
from app.modules.community_posts.domain.exceptions import (
    InsufficientPostRoleError,
    PostMembershipRequiredError,
    PostNotViewableError,
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
        raise PostMembershipRequiredError(community_id, user_id)
    return member


def ensure_can_create(
    member: CommunityMemberSummaryDTO | None, *, community_id: UUID, user_id: UUID
) -> None:
    _ensure_active_member(member, community_id=community_id, user_id=user_id)


def ensure_can_author_action(
    member: CommunityMemberSummaryDTO | None,
    *,
    community_id: UUID,
    user_id: UUID,
    author_id: UUID,
) -> None:
    if user_id == author_id:
        return
    active_member = _ensure_active_member(member, community_id=community_id, user_id=user_id)
    if _ROLE_RANK[active_member.role] < _ROLE_RANK[CommunityRole.MODERATOR]:
        raise InsufficientPostRoleError(community_id, user_id)


def ensure_is_moderator(
    member: CommunityMemberSummaryDTO | None, *, community_id: UUID, user_id: UUID
) -> None:
    active_member = _ensure_active_member(member, community_id=community_id, user_id=user_id)
    if _ROLE_RANK[active_member.role] < _ROLE_RANK[CommunityRole.MODERATOR]:
        raise InsufficientPostRoleError(community_id, user_id)


def _is_active_moderator_or_above(member: CommunityMemberSummaryDTO | None) -> bool:
    return (
        member is not None
        and member.status is CommunityMemberStatus.ACTIVE
        and _ROLE_RANK[member.role] >= _ROLE_RANK[CommunityRole.MODERATOR]
    )


def ensure_can_view(
    post: CommunityPost, member: CommunityMemberSummaryDTO | None, *, user_id: UUID | None
) -> None:
    if post.visibility is PostVisibility.PUBLIC:
        return
    if post.visibility is PostVisibility.MEMBERS_ONLY:
        if member is not None and member.status is CommunityMemberStatus.ACTIVE:
            return
        raise PostNotViewableError(post.id)
    # PRIVATE: only the author or a moderator-or-above may view it.
    if user_id is not None and user_id == post.author_id:
        return
    if _is_active_moderator_or_above(member):
        return
    raise PostNotViewableError(post.id)
