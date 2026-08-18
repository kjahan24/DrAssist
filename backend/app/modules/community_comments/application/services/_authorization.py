"""Role-hierarchy authorization helpers shared by every mutating Community
Comments service.

Mirrors `app.modules.community_answers.application.services
._authorization` exactly for the ordinary author/moderator shapes — see
that module's own docstring for the full "operates on
`CommunityMemberSummaryDTO`, not a domain entity this module has no
database access to" reasoning, which applies identically here.

Authorization split, matching this task's own FEATURES/APPLICATION/
SECURITY sections:
- `ensure_can_create` (CreateComment/CreateReply): any active community
  member may post.
- `ensure_can_author_action` (Update/Delete/Publish/Archive/Restore, for
  either a comment or a reply — see `CommunityComment`'s own module
  docstring for why there is only one such helper): the acting user must
  be either the comment's own author, or hold at least `MODERATOR` in the
  comment's own community.
- `ensure_can_view` (GetComment/ListComments/ListReplies/GetThread/
  SearchComments): a `PUBLISHED` comment is visible to anyone who can
  reach this module's API at all (there is no per-comment visibility
  tier — see `CommunityComment`'s own module docstring for why); any
  other status is visible only to the comment's own author or a
  moderator-or-above. This collapses `CommunityAnswer`'s own three-tier
  `AnswerVisibility` split (`PUBLIC`/`MEMBERS_ONLY`/`PRIVATE`) into one
  boundary (`PUBLISHED` vs. everything else), since Comments has no
  independent visibility concept to gate on.
- `ensure_can_view_target` (CreateComment only, before a *top-level*
  comment may even be written): enforces the *target's* own visibility
  tier — compared by raw string value, not by importing three different
  peer modules' own visibility enums, see `_target_resolution`'s own
  docstring for why. `CreateReplyService` never needs this: a reply's
  viewability gate is its own parent's `PUBLISHED` status (checked via
  `ParentCommentNotAcceptingRepliesError`), not the original target's
  visibility tier a second time.
"""

from uuid import UUID

from app.modules.community.public.dto import (
    CommunityMemberStatus,
    CommunityMemberSummaryDTO,
    CommunityRole,
)
from app.modules.community_comments.domain.entities import CommunityComment
from app.modules.community_comments.domain.enums import CommentStatus
from app.modules.community_comments.domain.exceptions import (
    CommentMembershipRequiredError,
    CommentNotViewableError,
    InsufficientCommentRoleError,
    TargetNotViewableForCommentError,
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
        raise CommentMembershipRequiredError(community_id, user_id)
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
        raise InsufficientCommentRoleError(community_id, user_id)


def _is_active_moderator_or_above(member: CommunityMemberSummaryDTO | None) -> bool:
    return (
        member is not None
        and member.status is CommunityMemberStatus.ACTIVE
        and _ROLE_RANK[member.role] >= _ROLE_RANK[CommunityRole.MODERATOR]
    )


def ensure_can_view(
    comment: CommunityComment, member: CommunityMemberSummaryDTO | None, *, user_id: UUID | None
) -> None:
    if comment.status is CommentStatus.PUBLISHED:
        return
    if user_id is not None and user_id == comment.author_id:
        return
    if _is_active_moderator_or_above(member):
        return
    raise CommentNotViewableError(comment.id)


def ensure_can_view_target(
    *,
    target_id: UUID,
    visibility_value: str,
    target_author_id: UUID | None,
    member: CommunityMemberSummaryDTO | None,
    user_id: UUID | None,
) -> None:
    if visibility_value == "public":
        return
    if visibility_value == "members_only":
        if member is not None and member.status is CommunityMemberStatus.ACTIVE:
            return
        raise TargetNotViewableForCommentError(target_id)
    # private
    if user_id is not None and target_author_id is not None and user_id == target_author_id:
        return
    if _is_active_moderator_or_above(member):
        return
    raise TargetNotViewableForCommentError(target_id)
