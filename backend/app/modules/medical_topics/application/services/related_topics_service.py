"""`RelatedTopicsService` — resolves the "Related Topics" graph for one
topic into full topic summaries. Read-only: creating/removing relation
edges is `ManageTopicRelationsService`'s job (not named in this task's
own APPLICATION list, added the same way
`app.modules.community.application.services
.create_community_category_service.CreateCommunityCategoryService` was
added in Phase 5.2 to satisfy an explicit requirement — here, the
REPOSITORIES section's own relation CRUD — the use-case list otherwise
omits).

Restricted to `PUBLISHED`+`PUBLIC` related topics only — the same public-
discovery restriction `SearchTopicsService`/`TrendingTopicsService`/
`FeaturedTopicsService` already apply, so a "related topics" widget never
surfaces a draft/archived/private topic.
"""

from collections.abc import Sequence
from uuid import UUID

from app.modules.medical_topics.application.dto import RelatedTopicsInput, RelatedTopicsOutput
from app.modules.medical_topics.application.services._summary_mappers import topic_to_summary
from app.modules.medical_topics.domain.entities import MedicalTopicRelation
from app.modules.medical_topics.domain.enums import TopicStatus, TopicVisibility
from app.modules.medical_topics.domain.repositories import (
    MedicalTopicRelationRepository,
    MedicalTopicRepository,
)


class RelatedTopicsService:
    def __init__(
        self,
        *,
        topic_repository: MedicalTopicRepository,
        relation_repository: MedicalTopicRelationRepository,
    ) -> None:
        self._topics = topic_repository
        self._relations = relation_repository

    async def get_related(self, input_dto: RelatedTopicsInput) -> RelatedTopicsOutput:
        relations = await self._relations.list_related(input_dto.topic_id)
        related_ids = self._other_side_ids(input_dto.topic_id, relations)
        if not related_ids:
            return RelatedTopicsOutput(items=())

        topics = await self._topics.list_by_ids(related_ids[: input_dto.limit])
        discoverable = [
            t
            for t in topics
            if t.status is TopicStatus.PUBLISHED and t.visibility is TopicVisibility.PUBLIC
        ]
        return RelatedTopicsOutput(items=tuple(topic_to_summary(t) for t in discoverable))

    @staticmethod
    def _other_side_ids(topic_id: UUID, relations: Sequence[MedicalTopicRelation]) -> list[UUID]:
        ids: list[UUID] = []
        for relation in relations:
            other = (
                relation.related_topic_id
                if relation.topic_id.value == topic_id
                else relation.topic_id.value
            )
            if other not in ids:
                ids.append(other)
        return ids
