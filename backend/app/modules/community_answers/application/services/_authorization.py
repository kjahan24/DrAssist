"""Role-hierarchy authorization helpers shared by every mutating Community
Answers service.

Mirrors `app.modules.community_questions.application.services
._authorization` exactly for the ordinary author/moderator shapes — see
that module's own docstring for the full "operates on
`CommunityMemberSummaryDTO`, not a domain entity this module has no
database access to" reasoning, which applies identically here.

Authorization split, matching this task's own FEATURES/APPLICATION/
SECURITY sections:
- `ensure_can_create` (Create): any active community member may submit
  an answer.
- `ensure_can_author_action` (Update/Delete/Publish/Archive/Restore): the
  acting user must be either the answer's own author, or hold at least
  `MODERATOR` in the answer's community.
- `ensure_is_moderator` (Feature/Pin): moderator-only, no author
  exception — the same reasoning `CommunityPost.set_pinned`'s own
  docstring gives for pinning being an always-moderation action.
- `ensure_can_view` (GetAnswer): enforces `AnswerVisibility` — see that
  enum's own docstring for the three tiers.
- `ensure_can_view_question` (Create, before an answer may even be
  written): enforces the *question's* own `QuestionVisibility` against
  the `CommunityQuestionSummaryDTO` returned by `QuestionQueryPort` — a
  caller who cannot see a question should not be able to answer it
  either. Distinct from `ensure_can_view` because it operates on a
  cross-module summary DTO, not a domain entity this module has no
  database access to (the same reason `ensure_can_author_action` and
  `ensure_can_view` themselves operate on DTOs rather than entities).
- `ensure_can_select_best_answer` (MarkBestAnswer/RemoveBestAnswer): a
  *different* authorization subject than every other action here — this
  task's own DOMAIN section frames best-answer selection as the
  question-asker's own call (the same real-world Quora/StackOverflow
  convention: the person who asked chooses which answer helped them),
  not the answering author's; a moderator may still override. Takes the
  *question's* author id (not the answer's), resolved by the caller via
  `QuestionQueryPort.get_question_summary`.
"""

from uuid import UUID

from app.modules.community.public.dto import (
    CommunityMemberStatus,
    CommunityMemberSummaryDTO,
    CommunityRole,
)
from app.modules.community_answers.domain.entities import CommunityAnswer
from app.modules.community_answers.domain.enums import AnswerVisibility
from app.modules.community_answers.domain.exceptions import (
    AnswerMembershipRequiredError,
    AnswerNotViewableError,
    InsufficientAnswerRoleError,
    InsufficientBestAnswerRoleError,
    QuestionNotViewableForAnswerError,
)
from app.modules.community_questions.public.dto import CommunityQuestionSummaryDTO
from app.modules.community_questions.public.dto import QuestionVisibility as _QuestionVisibility

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
        raise AnswerMembershipRequiredError(community_id, user_id)
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
        raise InsufficientAnswerRoleError(community_id, user_id)


def ensure_is_moderator(
    member: CommunityMemberSummaryDTO | None, *, community_id: UUID, user_id: UUID
) -> None:
    active_member = _ensure_active_member(member, community_id=community_id, user_id=user_id)
    if _ROLE_RANK[active_member.role] < _ROLE_RANK[CommunityRole.MODERATOR]:
        raise InsufficientAnswerRoleError(community_id, user_id)


def _is_active_moderator_or_above(member: CommunityMemberSummaryDTO | None) -> bool:
    return (
        member is not None
        and member.status is CommunityMemberStatus.ACTIVE
        and _ROLE_RANK[member.role] >= _ROLE_RANK[CommunityRole.MODERATOR]
    )


def ensure_can_view(
    answer: CommunityAnswer, member: CommunityMemberSummaryDTO | None, *, user_id: UUID | None
) -> None:
    if answer.visibility is AnswerVisibility.PUBLIC:
        return
    if answer.visibility is AnswerVisibility.MEMBERS_ONLY:
        if member is not None and member.status is CommunityMemberStatus.ACTIVE:
            return
        raise AnswerNotViewableError(answer.id)
    # PRIVATE: only the author or a moderator-or-above may view it.
    if user_id is not None and user_id == answer.author_id:
        return
    if _is_active_moderator_or_above(member):
        return
    raise AnswerNotViewableError(answer.id)


def ensure_can_view_question(
    question: CommunityQuestionSummaryDTO,
    member: CommunityMemberSummaryDTO | None,
    *,
    user_id: UUID | None,
) -> None:
    if question.visibility is _QuestionVisibility.PUBLIC:
        return
    if question.visibility is _QuestionVisibility.MEMBERS_ONLY:
        if member is not None and member.status is CommunityMemberStatus.ACTIVE:
            return
        raise QuestionNotViewableForAnswerError(question.question_id)
    # PRIVATE
    if user_id is not None and user_id == question.author_id:
        return
    if _is_active_moderator_or_above(member):
        return
    raise QuestionNotViewableForAnswerError(question.question_id)


def ensure_can_select_best_answer(
    member: CommunityMemberSummaryDTO | None,
    *,
    community_id: UUID,
    user_id: UUID,
    question_id: UUID,
    question_author_id: UUID,
) -> None:
    if user_id == question_author_id:
        return
    active_member = _ensure_active_member(member, community_id=community_id, user_id=user_id)
    if _ROLE_RANK[active_member.role] < _ROLE_RANK[CommunityRole.MODERATOR]:
        raise InsufficientBestAnswerRoleError(question_id, user_id)
