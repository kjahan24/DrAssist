"""`UpdateTopicService` — the cycle-detection half of `parent_id`
reassignment `MedicalTopic.update_profile` itself explicitly defers (see
that method's own docstring): walks the proposed new parent's own
ancestor chain via `MedicalTopicRepository.get_by_id`, and rejects the
change if `topic_id` itself appears in it (assigning a descendant as your
own parent would otherwise create a cycle a naive single-aggregate check
can't see).
"""

from uuid import UUID

from app.modules.medical_topics.application.dto import UpdateTopicInput, UpdateTopicOutput
from app.modules.medical_topics.domain.exceptions import (
    CircularTopicHierarchyError,
    ParentTopicNotFoundError,
    TopicNotFoundError,
    TopicSpecialtyNotFoundError,
)
from app.modules.medical_topics.domain.repositories import (
    MedicalTopicRepository,
    TopicSpecialtyRepository,
)
from app.modules.medical_topics.domain.value_objects import (
    TopicColor,
    TopicDescription,
    TopicName,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase

_MAX_ANCESTOR_DEPTH = 1000


class UpdateTopicService(UseCase[UpdateTopicInput, UpdateTopicOutput]):
    def __init__(
        self,
        *,
        topic_repository: MedicalTopicRepository,
        specialty_repository: TopicSpecialtyRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._topics = topic_repository
        self._specialties = specialty_repository
        self._uow = unit_of_work

    async def _ensure_no_cycle(self, topic_id: UUID, proposed_parent_id: UUID) -> None:
        current: UUID | None = proposed_parent_id
        visited = 0
        while current is not None and visited < _MAX_ANCESTOR_DEPTH:
            if current == topic_id:
                raise CircularTopicHierarchyError(topic_id, proposed_parent_id)
            ancestor = await self._topics.get_by_id(current)
            current = ancestor.parent_id if ancestor is not None else None
            visited += 1

    async def execute(self, input_dto: UpdateTopicInput) -> UpdateTopicOutput:
        topic = await self._topics.get_by_id(input_dto.topic_id)
        if topic is None:
            raise TopicNotFoundError(input_dto.topic_id)

        if input_dto.parent_id is not None and not input_dto.clear_parent:
            if await self._topics.get_by_id(input_dto.parent_id) is None:
                raise ParentTopicNotFoundError(input_dto.parent_id)
            await self._ensure_no_cycle(input_dto.topic_id, input_dto.parent_id)

        if (
            input_dto.specialty_id is not None
            and not input_dto.clear_specialty
            and await self._specialties.get_by_id(input_dto.specialty_id) is None
        ):
            raise TopicSpecialtyNotFoundError(input_dto.specialty_id)

        topic.update_profile(
            name=TopicName(input_dto.name) if input_dto.name is not None else None,
            description=TopicDescription(input_dto.description)
            if input_dto.description is not None
            else None,
            clear_description=input_dto.clear_description,
            icon=input_dto.icon,
            clear_icon=input_dto.clear_icon,
            color=TopicColor(input_dto.color) if input_dto.color is not None else None,
            clear_color=input_dto.clear_color,
            status=input_dto.status,
            visibility=input_dto.visibility,
            parent_id=input_dto.parent_id,
            clear_parent=input_dto.clear_parent,
            specialty_id=input_dto.specialty_id,
            clear_specialty=input_dto.clear_specialty,
            updated_by=input_dto.updated_by,
        )

        await self._topics.add(topic)
        self._uow.collect_events(topic.pull_events())
        await self._uow.commit()

        return UpdateTopicOutput(
            topic_id=topic.id,
            name=str(topic.name),
            status=topic.status,
            visibility=topic.visibility,
        )
