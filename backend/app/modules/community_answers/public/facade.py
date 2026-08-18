"""`AnswerFacade` — the one concrete implementation of
`AnswerQueryPort`. Constructed per-request by
`app.modules.community_answers.container.build_answer_facade`, bound to
that request's `AsyncSession`.

Deliberately built directly against `CommunityAnswerRepository`, not
`GetAnswerService` — `GetAnswerService.get_by_id` enforces
`AnswerVisibility` for an end-user caller, which doesn't apply to a
module-to-module existence/summary check with no acting user in the
picture — the same reasoning `app.modules.community_questions.public
.facade.QuestionFacade` already establishes for itself.

Reuses `_summary_mappers.answer_to_summary` unchanged, so a
module-to-module summary lookup masks `author_id` for an anonymous
answer exactly like every other read path in this module — see that
mapper's own docstring.
"""

from uuid import UUID

from app.modules.community_answers.application.services._summary_mappers import (
    answer_to_summary,
)
from app.modules.community_answers.domain.repositories import CommunityAnswerRepository
from app.modules.community_answers.public.dto import CommunityAnswerSummaryDTO
from app.modules.community_answers.public.interfaces import AnswerQueryPort


class AnswerFacade(AnswerQueryPort):
    def __init__(self, *, answer_repository: CommunityAnswerRepository) -> None:
        self._answers = answer_repository

    async def answer_exists(self, answer_id: UUID) -> bool:
        return await self._answers.get_by_id(answer_id) is not None

    async def get_answer_summary(self, answer_id: UUID) -> CommunityAnswerSummaryDTO | None:
        answer = await self._answers.get_by_id(answer_id)
        return answer_to_summary(answer) if answer is not None else None
