"""`ListAuthorAnswersService` — one author's own published answer
history, across every question in the caller's own organization —
mirrors `BrowseAuthorQuestionsService` exactly; see
`ListQuestionAnswersService`'s own docstring for why "List" here still
means cursor-paginated."""

from app.modules.community_answers.application.dto import (
    AnswerFeedOutput,
    ListAuthorAnswersInput,
)
from app.modules.community_answers.application.services._summary_mappers import answer_to_summary
from app.modules.community_answers.domain.repositories import CommunityAnswerRepository


class ListAuthorAnswersService:
    def __init__(self, *, answer_repository: CommunityAnswerRepository) -> None:
        self._answers = answer_repository

    async def list_answers(self, input_dto: ListAuthorAnswersInput) -> AnswerFeedOutput:
        answers, next_cursor = await self._answers.browse_feed(
            organization_id=input_dto.organization_id,
            author_id=input_dto.author_id,
            cursor=input_dto.cursor,
            limit=input_dto.limit,
        )
        return AnswerFeedOutput(
            items=tuple(answer_to_summary(a) for a in answers), next_cursor=next_cursor
        )
