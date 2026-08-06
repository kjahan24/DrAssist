"""`ManageTopicAliasesService` — create/list/delete a topic's own
aliases/synonyms (see `MedicalTopicAlias`'s own docstring for why one
entity covers both FEATURES bullets). Not named in this task's own
APPLICATION list, but required to actually populate the alternate-name
data `SearchTopicsService` searches over — the same "add what's genuinely
required" precedent this module's own `CreateTopicSpecialtyService`
establishes for itself.
"""

from uuid import UUID

from app.modules.medical_topics.application.dto import (
    CreateTopicAliasInput,
    DeleteTopicAliasInput,
    TopicAliasSummaryDTO,
)
from app.modules.medical_topics.application.services._summary_mappers import alias_to_summary
from app.modules.medical_topics.domain.entities import MedicalTopicAlias
from app.modules.medical_topics.domain.exceptions import (
    DuplicateTopicAliasError,
    TopicAliasNotFoundError,
    TopicNotFoundError,
)
from app.modules.medical_topics.domain.repositories import (
    MedicalTopicAliasRepository,
    MedicalTopicRepository,
)
from app.modules.medical_topics.domain.value_objects import TopicId, TopicName
from app.shared.application.unit_of_work import UnitOfWork


class ManageTopicAliasesService:
    def __init__(
        self,
        *,
        alias_repository: MedicalTopicAliasRepository,
        topic_repository: MedicalTopicRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._aliases = alias_repository
        self._topics = topic_repository
        self._uow = unit_of_work

    async def create_alias(self, input_dto: CreateTopicAliasInput) -> TopicAliasSummaryDTO:
        if await self._topics.get_by_id(input_dto.topic_id) is None:
            raise TopicNotFoundError(input_dto.topic_id)

        alias_name = TopicName(input_dto.alias)
        existing = await self._aliases.list_by_topic(input_dto.topic_id)
        if any(str(a.alias) == str(alias_name) for a in existing):
            raise DuplicateTopicAliasError(input_dto.topic_id, str(alias_name))

        alias = MedicalTopicAlias.create(topic_id=TopicId(input_dto.topic_id), alias=alias_name)
        await self._aliases.add(alias)
        self._uow.collect_events(alias.pull_events())
        await self._uow.commit()

        return alias_to_summary(alias)

    async def list_aliases(self, topic_id: UUID) -> list[TopicAliasSummaryDTO]:
        aliases = await self._aliases.list_by_topic(topic_id)
        return [alias_to_summary(a) for a in aliases]

    async def delete_alias(self, input_dto: DeleteTopicAliasInput) -> None:
        alias = await self._aliases.get_by_id(input_dto.alias_id)
        if alias is None:
            raise TopicAliasNotFoundError(input_dto.alias_id)

        await self._aliases.remove(input_dto.alias_id)
        await self._uow.commit()
