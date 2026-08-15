"""`ManageQuestionTopicsService` — assign/list/unassign a question's own
*secondary* topics (this task's own DOMAIN section: "Optional secondary
Medical Topics"). Not named in this task's own APPLICATION list — the
same "add what's genuinely required" precedent
`app.modules.community_posts.application.services.manage_post_topics_service
.ManagePostTopicsService` establishes for itself. Author-or-moderator
authorized, the same rule `UpdateQuestionService` uses.

`assign_topic` additionally rejects assigning the question's own
`primary_topic_id` as a secondary topic too — a topic that's already the
*primary* one is, for this module's purposes, already "assigned"; this
task's own DOMAIN section frames "primary" and "secondary" as mutually
exclusive slots, not overlapping ones.
"""

from uuid import UUID

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_questions.application.dto import (
    AssignQuestionTopicInput,
    QuestionTopicSummaryDTO,
    UnassignQuestionTopicInput,
)
from app.modules.community_questions.application.services._authorization import (
    ensure_can_author_action,
)
from app.modules.community_questions.application.services._summary_mappers import (
    question_topic_to_summary,
)
from app.modules.community_questions.domain.entities import CommunityQuestionTopic
from app.modules.community_questions.domain.exceptions import (
    DuplicateQuestionTopicError,
    QuestionNotFoundError,
    QuestionTopicNotFoundError,
    TopicNotFoundForQuestionError,
)
from app.modules.community_questions.domain.repositories import (
    CommunityQuestionRepository,
    CommunityQuestionTopicRepository,
)
from app.modules.community_questions.domain.value_objects import QuestionId
from app.modules.medical_topics.public.interfaces import TopicQueryPort
from app.shared.application.unit_of_work import UnitOfWork


class ManageQuestionTopicsService:
    def __init__(
        self,
        *,
        question_topic_repository: CommunityQuestionTopicRepository,
        question_repository: CommunityQuestionRepository,
        community_query_port: CommunityQueryPort,
        topic_query_port: TopicQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._question_topics = question_topic_repository
        self._questions = question_repository
        self._communities = community_query_port
        self._topics = topic_query_port
        self._uow = unit_of_work

    async def assign_topic(self, input_dto: AssignQuestionTopicInput) -> QuestionTopicSummaryDTO:
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

        if not await self._topics.topic_exists(input_dto.topic_id):
            raise TopicNotFoundForQuestionError(input_dto.topic_id)

        if (
            input_dto.topic_id == question.primary_topic_id
            or await self._question_topics.is_assigned(input_dto.question_id, input_dto.topic_id)
        ):
            raise DuplicateQuestionTopicError(input_dto.question_id, input_dto.topic_id)

        assignment = CommunityQuestionTopic.create(
            question_id=QuestionId(input_dto.question_id), topic_id=input_dto.topic_id
        )
        await self._question_topics.add(assignment)
        self._uow.collect_events(assignment.pull_events())
        await self._uow.commit()

        return question_topic_to_summary(assignment)

    async def list_topics(self, question_id: UUID) -> list[QuestionTopicSummaryDTO]:
        assignments = await self._question_topics.list_by_question(question_id)
        return [question_topic_to_summary(a) for a in assignments]

    async def unassign_topic(self, input_dto: UnassignQuestionTopicInput) -> None:
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

        assignment = await self._question_topics.get_by_id(input_dto.question_topic_id)
        if assignment is None or assignment.question_id.value != input_dto.question_id:
            raise QuestionTopicNotFoundError(input_dto.question_topic_id)

        await self._question_topics.remove(input_dto.question_topic_id)
        await self._uow.commit()
