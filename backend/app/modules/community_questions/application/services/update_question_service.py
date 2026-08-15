"""`UpdateQuestionService` — the author (or a community moderator/admin)
may edit a question's own content — see
`_authorization.ensure_can_author_action` for the exact rule."""

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_questions.application.dto import (
    UpdateQuestionInput,
    UpdateQuestionOutput,
)
from app.modules.community_questions.application.services._authorization import (
    ensure_can_author_action,
)
from app.modules.community_questions.domain.exceptions import QuestionNotFoundError
from app.modules.community_questions.domain.repositories import CommunityQuestionRepository
from app.modules.community_questions.domain.value_objects import QuestionSummary, QuestionTitle
from app.shared.application.unit_of_work import UnitOfWork


class UpdateQuestionService:
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

    async def execute(self, input_dto: UpdateQuestionInput) -> UpdateQuestionOutput:
        question = await self._questions.get_by_id(input_dto.question_id)
        if question is None:
            raise QuestionNotFoundError(input_dto.question_id)

        member = await self._communities.get_membership(
            question.community_id, input_dto.acting_user_id
        )
        ensure_can_author_action(
            member,
            community_id=question.community_id,
            user_id=input_dto.acting_user_id,
            author_id=question.author_id,
        )

        question.update_content(
            title=QuestionTitle(input_dto.title) if input_dto.title is not None else None,
            body=input_dto.body,
            summary=QuestionSummary(input_dto.summary) if input_dto.summary is not None else None,
            regenerate_summary=input_dto.regenerate_summary,
            question_type=input_dto.question_type,
            visibility=input_dto.visibility,
            is_anonymous=input_dto.is_anonymous,
            updated_by=input_dto.acting_user_id,
        )

        await self._questions.add(question)
        self._uow.collect_events(question.pull_events())
        await self._uow.commit()

        return UpdateQuestionOutput(
            question_id=question.id,
            title=str(question.title),
            status=question.status,
            visibility=question.visibility,
        )
