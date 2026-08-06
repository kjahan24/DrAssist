"""`DeleteTopicService` — soft-deletes a `MedicalTopic`. Added to satisfy
this task's own explicit "CRUD" requirement, which its APPLICATION
section otherwise omits — the same "add what's genuinely required to
fulfill an explicit requirement" precedent
`app.modules.community.application.services.delete_community_service
.DeleteCommunityService` was added under in Phase 5.1.
"""

from app.modules.medical_topics.application.dto import DeleteTopicInput
from app.modules.medical_topics.domain.exceptions import TopicNotFoundError
from app.modules.medical_topics.domain.repositories import MedicalTopicRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class DeleteTopicService(UseCase[DeleteTopicInput, None]):
    def __init__(
        self, *, topic_repository: MedicalTopicRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._topics = topic_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: DeleteTopicInput) -> None:
        topic = await self._topics.get_by_id(input_dto.topic_id)
        if topic is None:
            raise TopicNotFoundError(input_dto.topic_id)

        await self._topics.remove(input_dto.topic_id)
        await self._uow.commit()
