"""`MarkBestAnswerService` — selects `answer_id` as the best answer for
`question_id`, enforcing every DOMAIN-section rule this task names:

- "Best Answer must belong to the same Question": `answer.question_id`
  is checked against the input's own `question_id`, raising
  `AnswerDoesNotBelongToQuestionError` on a mismatch — this is the one
  place in the module where a caller-supplied `question_id` is validated
  against the answer's own stored value rather than simply trusted,
  precisely because this task's own wording calls it out as an explicit
  rule to *enforce*, not just a structural given.
- "Only valid published answers can become Best Answer": enforced by
  `CommunityAnswer.mark_as_best` itself.
- "A Question can have only one Best Answer": enforced here, not on the
  entity — a single aggregate cannot see its own sibling rows, so this
  service looks up any existing best answer for the question via
  `CommunityAnswerRepository.get_best_answer_for_question` and clears it
  (`remove_best()`) in the *same* transaction as marking the new one,
  after the new answer's own `mark_as_best()` call has already succeeded
  (so an invalid target — e.g. still a draft — fails fast before the
  existing best answer is touched at all).

Authorization is the question-asker's own call (or a moderator override)
— see `_authorization.ensure_can_select_best_answer`'s own docstring for
why this is a different subject than every other answer action.
"""

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_answers.application.dto import (
    CommunityAnswerSummaryDTO,
    MarkBestAnswerInput,
)
from app.modules.community_answers.application.services._authorization import (
    ensure_can_select_best_answer,
)
from app.modules.community_answers.application.services._summary_mappers import (
    answer_to_summary,
)
from app.modules.community_answers.domain.exceptions import (
    AnswerDoesNotBelongToQuestionError,
    AnswerNotFoundError,
    QuestionNotFoundForAnswerError,
)
from app.modules.community_answers.domain.repositories import CommunityAnswerRepository
from app.modules.community_questions.public.interfaces import QuestionQueryPort
from app.shared.application.unit_of_work import UnitOfWork


class MarkBestAnswerService:
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

    async def execute(self, input_dto: MarkBestAnswerInput) -> CommunityAnswerSummaryDTO:
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

        answer.mark_as_best()
        events = list(answer.pull_events())

        previous_best = await self._answers.get_best_answer_for_question(input_dto.question_id)
        if previous_best is not None and previous_best.id != answer.id:
            previous_best.remove_best()
            await self._answers.add(previous_best)
            events.extend(previous_best.pull_events())

        await self._answers.add(answer)
        self._uow.collect_events(events)
        await self._uow.commit()

        return answer_to_summary(answer)
