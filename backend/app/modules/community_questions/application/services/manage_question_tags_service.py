"""`ManageQuestionTagsService` — assign/list/unassign a question's own
"Question Tags" (this task's own POST FEATURES bullet, adapted). Not
named in this task's own APPLICATION list — see
`ManageQuestionTopicsService`'s own docstring for the identical "add
what's genuinely required" reasoning and author-or-moderator
authorization rule.

Mirrors `app.modules.community_posts.application.services
.manage_post_tags_service.ManagePostTagsService` exactly: a question tag
is plain, per-question free text, not a reference to any shared
platform-wide tag vocabulary."""

from uuid import UUID

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_questions.application.dto import (
    AssignQuestionTagInput,
    QuestionTagSummaryDTO,
    UnassignQuestionTagInput,
)
from app.modules.community_questions.application.services._authorization import (
    ensure_can_author_action,
)
from app.modules.community_questions.application.services._summary_mappers import (
    question_tag_to_summary,
)
from app.modules.community_questions.domain.entities import CommunityQuestionTag
from app.modules.community_questions.domain.exceptions import (
    DuplicateQuestionTagError,
    QuestionNotFoundError,
    QuestionTagNotFoundError,
)
from app.modules.community_questions.domain.repositories import (
    CommunityQuestionRepository,
    CommunityQuestionTagRepository,
)
from app.modules.community_questions.domain.value_objects import QuestionId
from app.shared.application.unit_of_work import UnitOfWork


class ManageQuestionTagsService:
    def __init__(
        self,
        *,
        question_tag_repository: CommunityQuestionTagRepository,
        question_repository: CommunityQuestionRepository,
        community_query_port: CommunityQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._question_tags = question_tag_repository
        self._questions = question_repository
        self._communities = community_query_port
        self._uow = unit_of_work

    async def assign_tag(self, input_dto: AssignQuestionTagInput) -> QuestionTagSummaryDTO:
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

        normalized = input_dto.tag.strip().lower()
        if await self._question_tags.is_assigned(input_dto.question_id, normalized):
            raise DuplicateQuestionTagError(input_dto.question_id, normalized)

        assignment = CommunityQuestionTag.create(
            question_id=QuestionId(input_dto.question_id), tag=input_dto.tag
        )
        await self._question_tags.add(assignment)
        self._uow.collect_events(assignment.pull_events())
        await self._uow.commit()

        return question_tag_to_summary(assignment)

    async def list_tags(self, question_id: UUID) -> list[QuestionTagSummaryDTO]:
        assignments = await self._question_tags.list_by_question(question_id)
        return [question_tag_to_summary(a) for a in assignments]

    async def unassign_tag(self, input_dto: UnassignQuestionTagInput) -> None:
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

        assignment = await self._question_tags.get_by_id(input_dto.question_tag_id)
        if assignment is None or assignment.question_id.value != input_dto.question_id:
            raise QuestionTagNotFoundError(input_dto.question_tag_id)

        await self._question_tags.remove(input_dto.question_tag_id)
        await self._uow.commit()
