"""`ManageTopicRelationsService` — create/delete edges in the "Related
Topics" graph `RelatedTopicsService` reads (see that service's own
docstring for why this exists despite not being named in this task's own
APPLICATION list). `add_relation` checks `MedicalTopicRelationRepository
.exists` (symmetric) first and raises `DuplicateTopicRelationError` if
already present — the same "check-then-raise, not a silent no-op" shape
`ManageCommunityTagsService.assign_tag` establishes for its own
already-assigned check.
"""

from uuid import UUID

from app.modules.medical_topics.application.dto import (
    CreateTopicRelationInput,
    DeleteTopicRelationInput,
    TopicRelationSummaryDTO,
)
from app.modules.medical_topics.application.services._summary_mappers import relation_to_summary
from app.modules.medical_topics.domain.entities import MedicalTopicRelation
from app.modules.medical_topics.domain.enums import TopicRelationType
from app.modules.medical_topics.domain.exceptions import (
    DuplicateTopicRelationError,
    TopicNotFoundError,
    TopicRelationNotFoundError,
)
from app.modules.medical_topics.domain.repositories import (
    MedicalTopicRelationRepository,
    MedicalTopicRepository,
)
from app.modules.medical_topics.domain.value_objects import TopicId
from app.shared.application.unit_of_work import UnitOfWork


class ManageTopicRelationsService:
    def __init__(
        self,
        *,
        relation_repository: MedicalTopicRelationRepository,
        topic_repository: MedicalTopicRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._relations = relation_repository
        self._topics = topic_repository
        self._uow = unit_of_work

    async def add_relation(self, input_dto: CreateTopicRelationInput) -> TopicRelationSummaryDTO:
        if await self._topics.get_by_id(input_dto.topic_id) is None:
            raise TopicNotFoundError(input_dto.topic_id)
        if await self._topics.get_by_id(input_dto.related_topic_id) is None:
            raise TopicNotFoundError(input_dto.related_topic_id)

        if await self._relations.exists(input_dto.topic_id, input_dto.related_topic_id):
            raise DuplicateTopicRelationError(input_dto.topic_id, input_dto.related_topic_id)

        relation = MedicalTopicRelation.create(
            topic_id=TopicId(input_dto.topic_id),
            related_topic_id=input_dto.related_topic_id,
            relation_type=TopicRelationType(input_dto.relation_type),
        )
        await self._relations.add(relation)
        self._uow.collect_events(relation.pull_events())
        await self._uow.commit()

        return relation_to_summary(relation)

    async def list_relations(self, topic_id: UUID) -> list[TopicRelationSummaryDTO]:
        relations = await self._relations.list_related(topic_id)
        return [relation_to_summary(r) for r in relations]

    async def delete_relation(self, input_dto: DeleteTopicRelationInput) -> None:
        relation = await self._relations.get_by_id(input_dto.relation_id)
        if relation is None:
            raise TopicRelationNotFoundError(input_dto.relation_id)

        await self._relations.remove(input_dto.relation_id)
        await self._uow.commit()
