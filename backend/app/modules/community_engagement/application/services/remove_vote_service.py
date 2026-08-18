"""`RemoveVoteService` — "Removing a vote must be idempotent" (this
task's own DOMAIN RULES): if the acting user has no vote on this target
at all, this is a silent no-op, not an error. Never re-validates the
target's own existence/status/tenant — a user must always be able to
remove their own vote even if the underlying content was later archived
or deleted, see `entities.py`'s own module docstring for the full
"removal is unconditionally idempotent" reasoning shared by every
aggregate in this module.
"""

from app.modules.community_engagement.application.dto import RemoveVoteInput
from app.modules.community_engagement.domain.repositories import VoteRepository
from app.shared.application.unit_of_work import UnitOfWork


class RemoveVoteService:
    def __init__(self, *, vote_repository: VoteRepository, unit_of_work: UnitOfWork) -> None:
        self._votes = vote_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: RemoveVoteInput) -> None:
        existing = await self._votes.get_vote(
            input_dto.user_id, input_dto.target_type, input_dto.target_id
        )
        if existing is None:
            return

        existing.mark_removed()
        events = existing.pull_events()
        await self._votes.remove(existing.id)
        self._uow.collect_events(events)
        await self._uow.commit()
