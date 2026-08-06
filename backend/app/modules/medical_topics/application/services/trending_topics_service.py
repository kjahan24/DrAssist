"""`TrendingTopicsService` — the top topics by `trending_score`, restricted
to `PUBLISHED`+`PUBLIC` topics only (the public discovery surface — see
`SearchTopicsService`'s own docstring for the identical restriction and
reasoning)."""

from app.modules.medical_topics.application.dto import ListTopicsOutput, TrendingTopicsInput
from app.modules.medical_topics.application.services._summary_mappers import topic_to_summary
from app.modules.medical_topics.domain.enums import TopicStatus, TopicVisibility
from app.modules.medical_topics.domain.repositories import MedicalTopicRepository

_PUBLISHED = (TopicStatus.PUBLISHED,)
_PUBLIC = (TopicVisibility.PUBLIC,)


class TrendingTopicsService:
    def __init__(self, *, topic_repository: MedicalTopicRepository) -> None:
        self._topics = topic_repository

    async def get_trending(self, input_dto: TrendingTopicsInput) -> ListTopicsOutput:
        topics, total = await self._topics.search(
            status=_PUBLISHED,
            visibility=_PUBLIC,
            specialty_id=input_dto.specialty_id,
            sort_by="trending_score",
            sort_order="desc",
            offset=input_dto.offset,
            limit=input_dto.limit,
        )
        return ListTopicsOutput(items=tuple(topic_to_summary(t) for t in topics), total=total)
