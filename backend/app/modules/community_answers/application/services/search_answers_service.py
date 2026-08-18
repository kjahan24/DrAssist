"""`SearchAnswersService` — full-filter keyword search over answers,
backing this task's own QUERY/FILTERING section. Distinct from the
cursor-paginated `ListQuestionAnswersService`/`ListAuthorAnswersService`
feeds: this is the offset-paginated, unrestricted-by-status management/
search view — the same split
`app.modules.community_questions.application.services.search_questions_service
.SearchQuestionsService` draws against its own `Browse*` services.
"""

from app.modules.community_answers.application.dto import (
    SearchAnswersInput,
    SearchAnswersOutput,
)
from app.modules.community_answers.application.services._summary_mappers import answer_to_summary
from app.modules.community_answers.domain.repositories import CommunityAnswerRepository


class SearchAnswersService:
    def __init__(self, *, answer_repository: CommunityAnswerRepository) -> None:
        self._answers = answer_repository

    async def search(self, input_dto: SearchAnswersInput) -> SearchAnswersOutput:
        answers, total = await self._answers.search(
            organization_id=input_dto.organization_id,
            query=input_dto.query,
            question_id=input_dto.question_id,
            community_id=input_dto.community_id,
            topic_id=input_dto.topic_id,
            author_id=input_dto.author_id,
            status=input_dto.status,
            visibility=input_dto.visibility,
            best_answer_only=input_dto.best_answer_only,
            featured_only=input_dto.featured_only,
            pinned_only=input_dto.pinned_only,
            created_from=input_dto.created_from,
            created_to=input_dto.created_to,
            offset=input_dto.offset,
            limit=input_dto.limit,
        )
        return SearchAnswersOutput(items=tuple(answer_to_summary(a) for a in answers), total=total)
