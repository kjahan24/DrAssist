"""`CreateAnswerService` — provisions a new `CommunityAnswer` against an
existing, published `CommunityQuestion`.

Cross-module reads only, never a private repository import:
`QuestionQueryPort.get_question_summary` resolves the parent question's
own `community_id`/`organization_id`/`primary_topic_id` (denormalized
onto the new answer — see `CommunityAnswer`'s own module docstring) and
validates the question is actually open to new answers;
`CommunityQueryPort.get_membership` validates the acting author's
community membership.

Enforces, in order, this task's own DOMAIN section requirements:
"Answer must belong to an existing Question" (`QuestionNotFoundForAnswerError`
if `question_id` doesn't resolve), "Author must be authorized"
(`ensure_can_create` — any active community member), plus this module's
own additional guard that a question not currently `PUBLISHED` cannot
receive new answers (mirrors `CommunityQuestion.close`'s own "no longer
accepting new engagement" semantics from Phase 5.5) and that the acting
user must actually be able to *see* the question before answering it
(`ensure_can_view_question`).
"""

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_answers.application.dto import CreateAnswerInput, CreateAnswerOutput
from app.modules.community_answers.application.services._authorization import (
    ensure_can_create,
    ensure_can_view_question,
)
from app.modules.community_answers.domain.entities import CommunityAnswer
from app.modules.community_answers.domain.exceptions import (
    QuestionNotAcceptingAnswersError,
    QuestionNotFoundForAnswerError,
)
from app.modules.community_answers.domain.repositories import CommunityAnswerRepository
from app.modules.community_answers.domain.value_objects import AnswerBody, AnswerSummary
from app.modules.community_questions.public.dto import QuestionStatus
from app.modules.community_questions.public.interfaces import QuestionQueryPort
from app.shared.application.unit_of_work import UnitOfWork


class CreateAnswerService:
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

    async def execute(self, input_dto: CreateAnswerInput) -> CreateAnswerOutput:
        question = await self._questions.get_question_summary(input_dto.question_id)
        if question is None:
            raise QuestionNotFoundForAnswerError(input_dto.question_id)

        if question.status is not QuestionStatus.PUBLISHED:
            raise QuestionNotAcceptingAnswersError(input_dto.question_id)

        member = await self._communities.get_membership(question.community_id, input_dto.author_id)
        ensure_can_create(member, community_id=question.community_id, user_id=input_dto.author_id)
        ensure_can_view_question(question, member, user_id=input_dto.author_id)

        answer = CommunityAnswer.create(
            question_id=input_dto.question_id,
            community_id=question.community_id,
            organization_id=question.organization_id,
            topic_id=question.primary_topic_id,
            author_id=input_dto.author_id,
            body=AnswerBody(input_dto.body),
            summary=AnswerSummary(input_dto.summary) if input_dto.summary is not None else None,
            visibility=input_dto.visibility,
            is_anonymous=input_dto.is_anonymous,
        )
        await self._answers.add(answer)
        self._uow.collect_events(answer.pull_events())
        await self._uow.commit()

        return CreateAnswerOutput(
            answer_id=answer.id, question_id=answer.question_id, status=answer.status
        )
