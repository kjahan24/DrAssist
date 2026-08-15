"""`BrowseAuthorQuestionsService` — one author's own published/closed
question history, across every community in the caller's own
organization — mirrors `app.modules.community_posts.application.services
.browse_author_posts_service.BrowseAuthorPostsService` exactly."""

from app.modules.community_questions.application.dto import (
    BrowseAuthorQuestionsInput,
    QuestionFeedOutput,
)
from app.modules.community_questions.application.services._summary_mappers import (
    question_to_summary,
)
from app.modules.community_questions.domain.repositories import CommunityQuestionRepository


class BrowseAuthorQuestionsService:
    def __init__(self, *, question_repository: CommunityQuestionRepository) -> None:
        self._questions = question_repository

    async def browse(self, input_dto: BrowseAuthorQuestionsInput) -> QuestionFeedOutput:
        questions, next_cursor = await self._questions.browse_feed(
            organization_id=input_dto.organization_id,
            author_id=input_dto.author_id,
            cursor=input_dto.cursor,
            limit=input_dto.limit,
        )
        return QuestionFeedOutput(
            items=tuple(question_to_summary(q) for q in questions), next_cursor=next_cursor
        )
