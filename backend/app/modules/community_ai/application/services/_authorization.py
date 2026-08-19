"""Authorization for the Community AI Features module.

"AI analysis must never become a side-channel for accessing content the
requester cannot normally access" (this task's own AUTHORIZATION section)
is enforced here by reusing the *exact* `PostVisibility`/`QuestionVisibility`
/`AnswerVisibility` three-way branch (`PUBLIC` always viewable, `MEMBERS_ONLY`
requires active community membership, `PRIVATE` requires the author or a
`MODERATOR`-or-above community member) every content module's own
`application/services/_authorization.py::ensure_can_view` already
implements for its own end-user read paths — reimplemented locally against
the *raw string* `visibility_value`/role-rank shape (rather than importing
each module's own `PostVisibility`/etc. enum, which are not part of any
module's public surface) for the same "compare against a public port's own
raw values, never import a peer module's domain enum" reasoning
`_target_resolution.py`'s own docstring gives for `is_published`.

`COMMENT` (thread) targets have no `visibility_value` at all (see
`_target_resolution.py`'s own docstring) — authorized on active community
membership alone, which is *at least as strict* as `PUBLIC` (every
community member can already see `PUBLIC` content) and simpler than
`MEMBERS_ONLY`'s own bar, so this never under-authorizes relative to what
the four other target types would require in the least-restrictive case.

`ensure_not_moderated` additionally checks
`app.modules.community_moderation.public.interfaces.ModerationQueryPort
.get_content_moderation_status` — this task's own SAFETY section says
"Respect moderation restrictions" without scoping it to Similar
Discussions alone, so every analysis type checks it, not just that one
feature. `ModerationTargetType`'s members share identical string values
with this module's own `CommunityContentTargetType` (`"post"`/
`"question"`/`"answer"`/`"comment"`) by construction, so converting
between them is a plain `.value` round-trip, never a lossy mapping.
"""

from uuid import UUID

from app.modules.community.public.dto import (
    CommunityMemberStatus,
    CommunityMemberSummaryDTO,
    CommunityRole,
)
from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_ai.application.services._target_resolution import (
    ResolvedAnalysisTarget,
)
from app.modules.community_ai.domain.enums import CommunityContentTargetType
from app.modules.community_ai.domain.exceptions import AnalysisTargetNotFoundError
from app.modules.community_moderation.public.dto import ModerationTargetType
from app.modules.community_moderation.public.interfaces import ModerationQueryPort

_ROLE_RANK: dict[CommunityRole, int] = {
    CommunityRole.MEMBER: 0,
    CommunityRole.MODERATOR: 1,
    CommunityRole.ADMIN: 2,
    CommunityRole.OWNER: 3,
}

_PUBLIC = "public"
_MEMBERS_ONLY = "members_only"
_RESTRICTED_STATUSES = frozenset({"removed", "restricted"})


def _is_active_member(member: CommunityMemberSummaryDTO | None) -> bool:
    return member is not None and member.status is CommunityMemberStatus.ACTIVE


def _is_moderator_or_above(member: CommunityMemberSummaryDTO | None) -> bool:
    if not _is_active_member(member):
        return False
    assert member is not None
    return _ROLE_RANK[member.role] >= _ROLE_RANK[CommunityRole.MODERATOR]


async def ensure_can_access_target(
    resolved: ResolvedAnalysisTarget,
    *,
    target_id: UUID,
    requester_id: UUID,
    requester_organization_id: UUID,
    community_query_port: CommunityQueryPort,
) -> None:
    if resolved.organization_id != requester_organization_id:
        raise AnalysisTargetNotFoundError(target_id)

    if resolved.visibility_value is None or resolved.visibility_value == _PUBLIC:
        return

    member = await community_query_port.get_membership(resolved.community_id, requester_id)

    if resolved.visibility_value == _MEMBERS_ONLY:
        if _is_active_member(member):
            return
        raise AnalysisTargetNotFoundError(target_id)

    # PRIVATE: only the author or a moderator-or-above may access it.
    if resolved.author_id is not None and requester_id == resolved.author_id:
        return
    if _is_moderator_or_above(member):
        return
    raise AnalysisTargetNotFoundError(target_id)


async def ensure_not_moderated(
    target_type: CommunityContentTargetType,
    target_id: UUID,
    *,
    moderation_query_port: ModerationQueryPort,
) -> None:
    status = await moderation_query_port.get_content_moderation_status(
        ModerationTargetType(target_type.value), target_id
    )
    if status in _RESTRICTED_STATUSES:
        raise AnalysisTargetNotFoundError(target_id)
