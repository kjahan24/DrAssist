"""`UnsaveContentService` — unconditionally idempotent, the same shape
`remove_vote_service.RemoveVoteService` establishes for itself; see that
service's own docstring."""

from app.modules.community_engagement.application.dto import UnsaveContentInput
from app.modules.community_engagement.domain.repositories import SavedContentRepository
from app.shared.application.unit_of_work import UnitOfWork


class UnsaveContentService:
    def __init__(
        self, *, saved_content_repository: SavedContentRepository, unit_of_work: UnitOfWork
    ) -> None:
        self._saved = saved_content_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: UnsaveContentInput) -> None:
        existing = await self._saved.get_saved(
            input_dto.user_id, input_dto.target_type, input_dto.target_id
        )
        if existing is None:
            return

        existing.mark_removed()
        events = existing.pull_events()
        await self._saved.remove(existing.id)
        self._uow.collect_events(events)
        await self._uow.commit()
