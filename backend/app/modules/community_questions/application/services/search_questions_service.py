"""`SearchQuestionsService` — full-filter keyword search over questions,
backing this task's own SEARCH section. Distinct from the `Browse*Questions`
services: those are the cursor-paginated, PUBLISHED/CLOSED-only consumer
feeds; this is the offset-paginated, unrestricted-by-status management/
search view — the same split
`app.modules.community_posts.application.services.search_posts_service
.SearchPostsService` draws against its own `Browse*Feed` services.
"""

from app.modules.community_questions.application.dto import (
    SearchQuestionsInput,
    SearchQuestionsOutput,
)
from app.modules.community_questions.application.services._summary_mappers import (
    question_to_summary,
)
from app.modules.community_questions.domain.repositories import CommunityQuestionRepository


class SearchQuestionsService:
    def __init__(self, *, question_repository: CommunityQuestionRepository) -> None:
        self._questions = question_repository

    async def search(self, input_dto: SearchQuestionsInput) -> SearchQuestionsOutput:
        questions, total = await self._questions.search(
            organization_id=input_dto.organization_id,
            query=input_dto.query,
            community_id=input_dto.community_id,
            topic_id=input_dto.topic_id,
            author_id=input_dto.author_id,
            question_type=input_dto.question_type,
            status=input_dto.status,
            visibility=input_dto.visibility,
            pinned_only=input_dto.pinned_only,
            featured_only=input_dto.featured_only,
            created_from=input_dto.created_from,
            created_to=input_dto.created_to,
            offset=input_dto.offset,
            limit=input_dto.limit,
        )
        return SearchQuestionsOutput(
            items=tuple(question_to_summary(q) for q in questions), total=total
        )
