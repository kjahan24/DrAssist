"""`PinQuestionService` — community-moderator-only, no author exception —
see `CommunityQuestion.set_pinned`'s own docstring."""

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_questions.application.dto import SetQuestionPinnedInput
from app.modules.community_questions.application.services._authorization import (
    ensure_is_moderator,
)
from app.modules.community_questions.domain.exceptions import QuestionNotFoundError
from app.modules.community_questions.domain.repositories import CommunityQuestionRepository
from app.shared.application.unit_of_work import UnitOfWork


class PinQuestionService:
    def __init__(
        self,
        *,
        question_repository: CommunityQuestionRepository,
        community_query_port: CommunityQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._questions = question_repository
        self._communities = community_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: SetQuestionPinnedInput) -> None:
        question = await self._questions.get_by_id(input_dto.question_id)
        if question is None:
            raise QuestionNotFoundError(input_dto.question_id)

        member = await self._communities.get_membership(
            question.community_id, input_dto.acting_user_id
        )
        ensure_is_moderator(
            member, community_id=question.community_id, user_id=input_dto.acting_user_id
        )

        question.set_pinned(input_dto.pinned)
        await self._questions.add(question)
        self._uow.collect_events(question.pull_events())
        await self._uow.commit()
