"""`DeleteAnswerService` — the author (or a community moderator/admin)
may delete their own answer, the same authorization rule
`UpdateAnswerService` uses.

Deletion here is a domain-level status transition
(`CommunityAnswer.delete()`), persisted through the ordinary `add()`
upsert — see `AnswerStatus`'s own docstring for why."""

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_answers.application.dto import DeleteAnswerInput
from app.modules.community_answers.application.services._authorization import (
    ensure_can_author_action,
)
from app.modules.community_answers.domain.exceptions import AnswerNotFoundError
from app.modules.community_answers.domain.repositories import CommunityAnswerRepository
from app.shared.application.unit_of_work import UnitOfWork


class DeleteAnswerService:
    def __init__(
        self,
        *,
        answer_repository: CommunityAnswerRepository,
        community_query_port: CommunityQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._answers = answer_repository
        self._communities = community_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: DeleteAnswerInput) -> None:
        answer = await self._answers.get_by_id(input_dto.answer_id)
        if answer is None:
            raise AnswerNotFoundError(input_dto.answer_id)

        member = await self._communities.get_membership(
            answer.community_id, input_dto.acting_user_id
        )
        ensure_can_author_action(
            member,
            community_id=answer.community_id,
            user_id=input_dto.acting_user_id,
            author_id=answer.author_id,
        )

        answer.delete()
        await self._answers.add(answer)
        self._uow.collect_events(answer.pull_events())
        await self._uow.commit()
