"""`BrowseCommunityQuestionsService` — the Quora-style per-community
question feed, cursor-paginated, with pinned questions sorted first
(`pinned_first=True`) — mirrors `app.modules.community_posts.application
.services.browse_community_feed_service.BrowseCommunityFeedService`
exactly."""

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_questions.application.dto import (
    BrowseCommunityQuestionsInput,
    QuestionFeedOutput,
)
from app.modules.community_questions.application.services._summary_mappers import (
    question_to_summary,
)
from app.modules.community_questions.domain.exceptions import CommunityNotFoundForQuestionError
from app.modules.community_questions.domain.repositories import CommunityQuestionRepository


class BrowseCommunityQuestionsService:
    def __init__(
        self,
        *,
        question_repository: CommunityQuestionRepository,
        community_query_port: CommunityQueryPort,
    ) -> None:
        self._questions = question_repository
        self._communities = community_query_port

    async def browse(self, input_dto: BrowseCommunityQuestionsInput) -> QuestionFeedOutput:
        community = await self._communities.get_community_summary(input_dto.community_id)
        if community is None:
            raise CommunityNotFoundForQuestionError(input_dto.community_id)

        questions, next_cursor = await self._questions.browse_feed(
            organization_id=community.organization_id,
            community_id=input_dto.community_id,
            pinned_first=True,
            cursor=input_dto.cursor,
            limit=input_dto.limit,
        )
        return QuestionFeedOutput(
            items=tuple(question_to_summary(q) for q in questions), next_cursor=next_cursor
        )
