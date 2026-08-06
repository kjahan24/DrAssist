"""`BrowseTopicFeedService` — every published post assigned to one
`MedicalTopic`, across every community in the caller's own organization
(cursor-paginated — see `CommunityPostRepository.browse_feed`'s own
docstring). `organization_id` is required on the input (not resolved
from the topic, which is platform-wide — see `TopicVisibility`'s own
docstring — and therefore carries no tenant of its own)."""

from app.modules.community_posts.application.dto import BrowseTopicFeedInput, PostFeedOutput
from app.modules.community_posts.application.services._summary_mappers import post_to_summary
from app.modules.community_posts.domain.exceptions import TopicNotFoundForPostError
from app.modules.community_posts.domain.repositories import CommunityPostRepository
from app.modules.medical_topics.public.interfaces import TopicQueryPort


class BrowseTopicFeedService:
    def __init__(
        self, *, post_repository: CommunityPostRepository, topic_query_port: TopicQueryPort
    ) -> None:
        self._posts = post_repository
        self._topics = topic_query_port

    async def browse(self, input_dto: BrowseTopicFeedInput) -> PostFeedOutput:
        if not await self._topics.topic_exists(input_dto.topic_id):
            raise TopicNotFoundForPostError(input_dto.topic_id)

        posts, next_cursor = await self._posts.browse_feed(
            organization_id=input_dto.organization_id,
            topic_id=input_dto.topic_id,
            cursor=input_dto.cursor,
            limit=input_dto.limit,
        )
        return PostFeedOutput(
            items=tuple(post_to_summary(p) for p in posts), next_cursor=next_cursor
        )
