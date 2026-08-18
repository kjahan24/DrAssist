"""`UnfollowTopicService` — unconditionally idempotent, the same shape
`remove_vote_service.RemoveVoteService` establishes for itself."""

from app.modules.community_engagement.application.dto import UnfollowTopicInput
from app.modules.community_engagement.domain.repositories import TopicFollowerRepository
from app.shared.application.unit_of_work import UnitOfWork


class UnfollowTopicService:
    def __init__(
        self, *, topic_follower_repository: TopicFollowerRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._followers = topic_follower_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: UnfollowTopicInput) -> None:
        existing = await self._followers.get_follow(input_dto.user_id, input_dto.topic_id)
        if existing is None:
            return

        existing.mark_removed()
        events = existing.pull_events()
        await self._followers.remove(existing.id)
        self._uow.collect_events(events)
        await self._uow.commit()
