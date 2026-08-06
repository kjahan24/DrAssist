"""`TopicFacade` — the one concrete implementation of `TopicQueryPort`.
Constructed per-request by
`app.modules.medical_topics.container.build_topic_facade`, bound to that
request's `AsyncSession`.
"""

from uuid import UUID

from app.modules.medical_topics.application.services.topic_query_service import GetTopicService
from app.modules.medical_topics.public.dto import TopicSummaryDTO
from app.modules.medical_topics.public.interfaces import TopicQueryPort


class TopicFacade(TopicQueryPort):
    def __init__(self, *, query_service: GetTopicService) -> None:
        self._query_service = query_service

    async def topic_exists(self, topic_id: UUID) -> bool:
        return await self._query_service.get_by_id(topic_id) is not None

    async def get_topic_summary(self, topic_id: UUID) -> TopicSummaryDTO | None:
        return await self._query_service.get_by_id(topic_id)

    async def get_topic_summary_by_slug(self, slug: str) -> TopicSummaryDTO | None:
        return await self._query_service.get_by_slug(slug)
