"""`QuestionFacade` — the one concrete implementation of
`QuestionQueryPort`. Constructed per-request by
`app.modules.community_questions.container.build_question_facade`, bound
to that request's `AsyncSession`.

Deliberately built directly against `CommunityQuestionRepository`, not
`GetQuestionService` — `GetQuestionService.get_by_id` enforces
`QuestionVisibility` for an end-user caller, which doesn't apply to a
module-to-module existence/summary check with no acting user in the
picture — the same reasoning
`app.modules.community_posts.public.facade.PostFacade` already
establishes for itself.
"""

from uuid import UUID

from app.modules.community_questions.application.services._summary_mappers import (
    question_to_summary,
)
from app.modules.community_questions.domain.repositories import CommunityQuestionRepository
from app.modules.community_questions.public.dto import CommunityQuestionSummaryDTO
from app.modules.community_questions.public.interfaces import QuestionQueryPort


class QuestionFacade(QuestionQueryPort):
    def __init__(self, *, question_repository: CommunityQuestionRepository) -> None:
        self._questions = question_repository

    async def question_exists(self, question_id: UUID) -> bool:
        return await self._questions.get_by_id(question_id) is not None

    async def get_question_summary(self, question_id: UUID) -> CommunityQuestionSummaryDTO | None:
        question = await self._questions.get_by_id(question_id)
        return question_to_summary(question) if question is not None else None
