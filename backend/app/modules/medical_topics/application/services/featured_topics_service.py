"""`FeaturedTopicsService` — platform-level curation: listing featured
topics, and toggling a topic's own `is_featured` flag.

Deliberately **not** authorized via any per-resource role check (this
module has none — see `MedicalTopicRepository`'s own docstring):
authorization happens at the API layer, via
`app.api.deps.require_permission("topics.feature")` — the same split
`app.modules.community.application.services.feature_communities_service
.FeatureCommunitiesService` establishes for `Community.set_featured`.
"""

from app.modules.medical_topics.application.dto import (
    FeaturedTopicsInput,
    ListTopicsOutput,
    SetTopicFeaturedInput,
)
from app.modules.medical_topics.application.services._summary_mappers import topic_to_summary
from app.modules.medical_topics.domain.enums import TopicStatus, TopicVisibility
from app.modules.medical_topics.domain.exceptions import TopicNotFoundError
from app.modules.medical_topics.domain.repositories import MedicalTopicRepository
from app.shared.application.unit_of_work import UnitOfWork

_PUBLISHED = (TopicStatus.PUBLISHED,)
_PUBLIC = (TopicVisibility.PUBLIC,)


class FeaturedTopicsService:
    def __init__(
        self, *, topic_repository: MedicalTopicRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._topics = topic_repository
        self._uow = unit_of_work

    async def list_featured(self, input_dto: FeaturedTopicsInput) -> ListTopicsOutput:
        topics, total = await self._topics.search(
            featured_only=True,
            status=_PUBLISHED,
            visibility=_PUBLIC,
            offset=input_dto.offset,
            limit=input_dto.limit,
        )
        return ListTopicsOutput(items=tuple(topic_to_summary(t) for t in topics), total=total)

    async def set_featured(self, input_dto: SetTopicFeaturedInput) -> None:
        topic = await self._topics.get_by_id(input_dto.topic_id)
        if topic is None:
            raise TopicNotFoundError(input_dto.topic_id)
        topic.set_featured(input_dto.featured)
        await self._topics.add(topic)
        self._uow.collect_events(topic.pull_events())
        await self._uow.commit()
