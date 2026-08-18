"""`UnfollowDoctorService` — unconditionally idempotent, the same shape
`remove_vote_service.RemoveVoteService` establishes for itself."""

from app.modules.community_engagement.application.dto import UnfollowDoctorInput
from app.modules.community_engagement.domain.repositories import DoctorFollowerRepository
from app.shared.application.unit_of_work import UnitOfWork


class UnfollowDoctorService:
    def __init__(
        self, *, doctor_follower_repository: DoctorFollowerRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._followers = doctor_follower_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: UnfollowDoctorInput) -> None:
        existing = await self._followers.get_follow(
            input_dto.follower_user_id, input_dto.followed_user_id
        )
        if existing is None:
            return

        existing.mark_removed()
        events = existing.pull_events()
        await self._followers.remove(existing.id)
        self._uow.collect_events(events)
        await self._uow.commit()
