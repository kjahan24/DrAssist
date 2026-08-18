"""`ListQuestionAnswersService` — every published answer to one
question, cursor-paginated, with pinned answers sorted first
(`pinned_first=True`). Named "List" (matching this task's own
APPLICATION section literally) rather than "Browse" (the naming
`app.modules.community_posts`/`app.modules.community_questions` use for
their own cursor-paginated feeds) — but the underlying pagination *is*
still cursor-based, per this task's own QUERY/FILTERING section: "Use
cursor pagination. Default ordering should be deterministic." Mirrors
`BrowseCommunityQuestionsService` exactly in shape.
"""

from app.modules.community_answers.application.dto import (
    AnswerFeedOutput,
    ListQuestionAnswersInput,
)
from app.modules.community_answers.application.services._summary_mappers import answer_to_summary
from app.modules.community_answers.domain.repositories import CommunityAnswerRepository


class ListQuestionAnswersService:
    def __init__(self, *, answer_repository: CommunityAnswerRepository) -> None:
        self._answers = answer_repository

    async def list_answers(self, input_dto: ListQuestionAnswersInput) -> AnswerFeedOutput:
        answers, next_cursor = await self._answers.browse_feed(
            organization_id=input_dto.organization_id,
            question_id=input_dto.question_id,
            pinned_first=True,
            cursor=input_dto.cursor,
            limit=input_dto.limit,
        )
        return AnswerFeedOutput(
            items=tuple(answer_to_summary(a) for a in answers), next_cursor=next_cursor
        )
