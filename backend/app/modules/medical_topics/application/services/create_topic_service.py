"""`CreateTopicService` — provisions a new `MedicalTopic`. No per-resource
ownership/role model exists in this module (topics are a platform-wide,
shared taxonomy — see `MedicalTopicRepository`'s own docstring), so
authorization is enforced once, at the router layer, via
`Depends(require_permission("topics.write"))` rather than a service-level
role check — unlike Community's `_authorization.ensure_role_at_least`,
which exists specifically because a caller's role differs per-community.
"""

from app.modules.medical_topics.application.dto import CreateTopicInput, CreateTopicOutput
from app.modules.medical_topics.domain.entities import MedicalTopic
from app.modules.medical_topics.domain.exceptions import (
    DuplicateTopicSlugError,
    ParentTopicNotFoundError,
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
    TopicSlug,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class CreateTopicService(UseCase[CreateTopicInput, CreateTopicOutput]):
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

    async def execute(self, input_dto: CreateTopicInput) -> CreateTopicOutput:
        slug = TopicSlug(input_dto.slug)
        if await self._topics.get_by_slug(str(slug)) is not None:
            raise DuplicateTopicSlugError(str(slug))

        if (
            input_dto.parent_id is not None
            and await self._topics.get_by_id(input_dto.parent_id) is None
        ):
            raise ParentTopicNotFoundError(input_dto.parent_id)

        if (
            input_dto.specialty_id is not None
            and await self._specialties.get_by_id(input_dto.specialty_id) is None
        ):
            raise TopicSpecialtyNotFoundError(input_dto.specialty_id)

        topic = MedicalTopic.create(
            slug=slug,
            name=TopicName(input_dto.name),
            description=TopicDescription(input_dto.description)
            if input_dto.description is not None
            else None,
            icon=input_dto.icon,
            color=TopicColor(input_dto.color) if input_dto.color is not None else None,
            parent_id=input_dto.parent_id,
            specialty_id=input_dto.specialty_id,
            visibility=input_dto.visibility,
            created_by=input_dto.created_by,
        )
        await self._topics.add(topic)
        self._uow.collect_events(topic.pull_events())
        await self._uow.commit()

        return CreateTopicOutput(
            topic_id=topic.id,
            slug=str(topic.slug),
            name=str(topic.name),
            status=topic.status,
            visibility=topic.visibility,
        )
