"""Role-hierarchy authorization helpers shared by every mutating Community
Questions service.

Mirrors `app.modules.community_posts.application.services._authorization`
exactly — see that module's own docstring for the full "operates on
`CommunityMemberSummaryDTO`, not a domain entity this module has no
database access to" reasoning, which applies identically here.

Authorization split, matching this task's own FEATURES/APPLICATION
sections:
- `ensure_can_author_action` (Update/Delete/Publish/Archive/Close/
  Reopen): the acting user must be either the question's own author, or
  hold at least `MODERATOR` in the question's community.
- `ensure_is_moderator` (Pin/Feature): moderator-only, no author
  exception — the same reasoning `CommunityPost.set_pinned`'s own
  docstring gives for pinning being an always-moderation action.
- `ensure_can_create` (Create): any active community member may submit a
  question.
- `ensure_can_view` (Get, Follow/Unfollow): enforces `QuestionVisibility`
  — see that enum's own docstring for the three tiers. Following/
  unfollowing reuses this same check (see `ManageQuestionFollowersService`'s
  own docstring for why): following is a lightweight engagement action
  gated on the same "can this caller even see the question" bar as
  reading it, not on full community membership.
"""

from uuid import UUID

from app.modules.community.public.dto import (
    CommunityMemberStatus,
    CommunityMemberSummaryDTO,
    CommunityRole,
)
from app.modules.community_questions.domain.entities import CommunityQuestion
from app.modules.community_questions.domain.enums import QuestionVisibility
from app.modules.community_questions.domain.exceptions import (
    InsufficientQuestionRoleError,
    QuestionMembershipRequiredError,
    QuestionNotViewableError,
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
        raise QuestionMembershipRequiredError(community_id, user_id)
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
        raise InsufficientQuestionRoleError(community_id, user_id)


def ensure_is_moderator(
    member: CommunityMemberSummaryDTO | None, *, community_id: UUID, user_id: UUID
) -> None:
    active_member = _ensure_active_member(member, community_id=community_id, user_id=user_id)
    if _ROLE_RANK[active_member.role] < _ROLE_RANK[CommunityRole.MODERATOR]:
        raise InsufficientQuestionRoleError(community_id, user_id)


def _is_active_moderator_or_above(member: CommunityMemberSummaryDTO | None) -> bool:
    return (
        member is not None
        and member.status is CommunityMemberStatus.ACTIVE
        and _ROLE_RANK[member.role] >= _ROLE_RANK[CommunityRole.MODERATOR]
    )


def ensure_can_view(
    question: CommunityQuestion, member: CommunityMemberSummaryDTO | None, *, user_id: UUID | None
) -> None:
    if question.visibility is QuestionVisibility.PUBLIC:
        return
    if question.visibility is QuestionVisibility.MEMBERS_ONLY:
        if member is not None and member.status is CommunityMemberStatus.ACTIVE:
            return
        raise QuestionNotViewableError(question.id)
    # PRIVATE: only the author or a moderator-or-above may view it.
    if user_id is not None and user_id == question.author_id:
        return
    if _is_active_moderator_or_above(member):
        return
    raise QuestionNotViewableError(question.id)
