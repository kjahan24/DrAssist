"""`CreateTopicSpecialtyService` — the actual "extensibility" code path
for `TopicSpecialty` (see that entity's own docstring for why specialties
are a real table rather than a closed `StrEnum`). Not named in this
task's own APPLICATION list, but required to make "Architecture must be
extensible" true rather than aspirational — the same "add what's
genuinely required" precedent
`app.modules.community.application.services
.create_community_category_service.CreateCommunityCategoryService`
establishes for its own, analogous need.
"""

from app.modules.medical_topics.application.dto import (
    CreateTopicSpecialtyInput,
    CreateTopicSpecialtyOutput,
)
from app.modules.medical_topics.domain.entities import TopicSpecialty
from app.modules.medical_topics.domain.exceptions import DuplicateTopicSpecialtyNameError
from app.modules.medical_topics.domain.repositories import TopicSpecialtyRepository
from app.modules.medical_topics.domain.value_objects import TopicDescription, TopicName, TopicSlug
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class CreateTopicSpecialtyService(UseCase[CreateTopicSpecialtyInput, CreateTopicSpecialtyOutput]):
    def __init__(
        self, *, specialty_repository: TopicSpecialtyRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._specialties = specialty_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: CreateTopicSpecialtyInput) -> CreateTopicSpecialtyOutput:
        name = TopicName(input_dto.name)
        slug = TopicSlug(input_dto.slug)

        if await self._specialties.get_by_name(str(name)) is not None:
            raise DuplicateTopicSpecialtyNameError(str(name))

        specialty = TopicSpecialty.create(
            name=name,
            slug=slug,
            description=TopicDescription(input_dto.description)
            if input_dto.description is not None
            else None,
        )
        await self._specialties.add(specialty)
        self._uow.collect_events(specialty.pull_events())
        await self._uow.commit()

        return CreateTopicSpecialtyOutput(
            specialty_id=specialty.id, name=str(specialty.name), slug=str(specialty.slug)
        )
