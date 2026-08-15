"""`BrowseTopicQuestionsService` — every published/closed question
assigned to one `MedicalTopic` (either as primary or secondary — see
`CommunityQuestionRepository`'s own docstring), across every community in
the caller's own organization. `organization_id` is required on the
input (not resolved from the topic, which is platform-wide) — mirrors
`app.modules.community_posts.application.services.browse_topic_feed_service
.BrowseTopicFeedService` exactly."""

from app.modules.community_questions.application.dto import (
    BrowseTopicQuestionsInput,
    QuestionFeedOutput,
)
from app.modules.community_questions.application.services._summary_mappers import (
    question_to_summary,
)
from app.modules.community_questions.domain.exceptions import TopicNotFoundForQuestionError
from app.modules.community_questions.domain.repositories import CommunityQuestionRepository
from app.modules.medical_topics.public.interfaces import TopicQueryPort


class BrowseTopicQuestionsService:
    def __init__(
        self, *, question_repository: CommunityQuestionRepository, topic_query_port: TopicQueryPort
    ) -> None:
        self._questions = question_repository
        self._topics = topic_query_port

    async def browse(self, input_dto: BrowseTopicQuestionsInput) -> QuestionFeedOutput:
        if not await self._topics.topic_exists(input_dto.topic_id):
            raise TopicNotFoundForQuestionError(input_dto.topic_id)

        questions, next_cursor = await self._questions.browse_feed(
            organization_id=input_dto.organization_id,
            topic_id=input_dto.topic_id,
            cursor=input_dto.cursor,
            limit=input_dto.limit,
        )
        return QuestionFeedOutput(
            items=tuple(question_to_summary(q) for q in questions), next_cursor=next_cursor
        )
