"""`UnfollowTopicService` — the inverse of `FollowTopicService`; see that
service's own docstring for why no `require_permission` gate applies."""

from app.modules.medical_topics.application.dto import UnfollowTopicInput
from app.modules.medical_topics.domain.exceptions import TopicNotFollowedError
from app.modules.medical_topics.domain.repositories import MedicalTopicFollowerRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class UnfollowTopicService(UseCase[UnfollowTopicInput, None]):
    def __init__(
        self, *, follower_repository: MedicalTopicFollowerRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._followers = follower_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: UnfollowTopicInput) -> None:
        existing = await self._followers.get_by_topic_and_user(
            input_dto.topic_id, input_dto.user_id
        )
        if existing is None:
            raise TopicNotFollowedError(input_dto.topic_id, input_dto.user_id)

        await self._followers.remove(input_dto.topic_id, input_dto.user_id)
        await self._uow.commit()
