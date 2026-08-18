"""`RestoreAnswerService` — author-or-moderator authorized, the same
rule `UpdateAnswerService` uses. `CommunityAnswer.restore()` itself
enforces the ARCHIVED-or-DELETED-only precondition and always lands on
`DRAFT` — see that method's own docstring."""

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_answers.application.dto import (
    CommunityAnswerSummaryDTO,
    RestoreAnswerInput,
)
from app.modules.community_answers.application.services._authorization import (
    ensure_can_author_action,
)
from app.modules.community_answers.application.services._summary_mappers import (
    answer_to_summary,
)
from app.modules.community_answers.domain.exceptions import AnswerNotFoundError
from app.modules.community_answers.domain.repositories import CommunityAnswerRepository
from app.shared.application.unit_of_work import UnitOfWork


class RestoreAnswerService:
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

    async def execute(self, input_dto: RestoreAnswerInput) -> CommunityAnswerSummaryDTO:
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

        answer.restore()
        await self._answers.add(answer)
        self._uow.collect_events(answer.pull_events())
        await self._uow.commit()

        return answer_to_summary(answer)
