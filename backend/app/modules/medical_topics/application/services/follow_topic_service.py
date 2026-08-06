"""`FollowTopicService` — a normal end-user action (unlike topic content
management), open to any authenticated caller, no `require_permission`
gate — the same "join/leave don't need special permission, only an
authenticated identity" shape
`app.modules.community.application.services.join_community_service
.JoinCommunityService` already establishes for `Community` membership.
"""

from app.modules.medical_topics.application.dto import FollowTopicInput, FollowTopicOutput
from app.modules.medical_topics.domain.entities import MedicalTopicFollower
from app.modules.medical_topics.domain.exceptions import (
    TopicAlreadyFollowedError,
    TopicNotFoundError,
)
from app.modules.medical_topics.domain.repositories import (
    MedicalTopicFollowerRepository,
    MedicalTopicRepository,
)
from app.modules.medical_topics.domain.value_objects import TopicId
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase


class FollowTopicService(UseCase[FollowTopicInput, FollowTopicOutput]):
    def __init__(
        self,
        *,
        topic_repository: MedicalTopicRepository,
        follower_repository: MedicalTopicFollowerRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._topics = topic_repository
        self._followers = follower_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: FollowTopicInput) -> FollowTopicOutput:
        if await self._topics.get_by_id(input_dto.topic_id) is None:
            raise TopicNotFoundError(input_dto.topic_id)

        existing = await self._followers.get_by_topic_and_user(
            input_dto.topic_id, input_dto.user_id
        )
        if existing is not None:
            raise TopicAlreadyFollowedError(input_dto.topic_id, input_dto.user_id)

        follower = MedicalTopicFollower.create(
            topic_id=TopicId(input_dto.topic_id), user_id=input_dto.user_id
        )
        await self._followers.add(follower)
        self._uow.collect_events(follower.pull_events())
        await self._uow.commit()

        return FollowTopicOutput(
            follower_id=follower.id,
            topic_id=input_dto.topic_id,
            user_id=input_dto.user_id,
            followed_at=follower.created_at,
        )
