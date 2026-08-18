"""`RemoveBestAnswerService` — clears `answer_id` as the best answer for
`question_id`. Same "belongs to the same question" check
`MarkBestAnswerService` performs, and the same question-asker-or-
moderator authorization — see that service's own docstring and
`_authorization.ensure_can_select_best_answer`'s own docstring.
`CommunityAnswer.remove_best` itself raises if the answer isn't
currently the best answer.
"""

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_answers.application.dto import RemoveBestAnswerInput
from app.modules.community_answers.application.services._authorization import (
    ensure_can_select_best_answer,
)
from app.modules.community_answers.domain.exceptions import (
    AnswerDoesNotBelongToQuestionError,
    AnswerNotFoundError,
    QuestionNotFoundForAnswerError,
)
from app.modules.community_answers.domain.repositories import CommunityAnswerRepository
from app.modules.community_questions.public.interfaces import QuestionQueryPort
from app.shared.application.unit_of_work import UnitOfWork


class RemoveBestAnswerService:
    def __init__(
        self,
        *,
        answer_repository: CommunityAnswerRepository,
        community_query_port: CommunityQueryPort,
        question_query_port: QuestionQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._answers = answer_repository
        self._communities = community_query_port
        self._questions = question_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: RemoveBestAnswerInput) -> None:
        answer = await self._answers.get_by_id(input_dto.answer_id)
        if answer is None:
            raise AnswerNotFoundError(input_dto.answer_id)
        if answer.question_id != input_dto.question_id:
            raise AnswerDoesNotBelongToQuestionError(input_dto.answer_id, input_dto.question_id)

        question = await self._questions.get_question_summary(input_dto.question_id)
        if question is None:
            raise QuestionNotFoundForAnswerError(input_dto.question_id)

        member = await self._communities.get_membership(
            answer.community_id, input_dto.acting_user_id
        )
        ensure_can_select_best_answer(
            member,
            community_id=answer.community_id,
            user_id=input_dto.acting_user_id,
            question_id=input_dto.question_id,
            question_author_id=question.author_id,
        )

        answer.remove_best()
        await self._answers.add(answer)
        self._uow.collect_events(answer.pull_events())
        await self._uow.commit()
