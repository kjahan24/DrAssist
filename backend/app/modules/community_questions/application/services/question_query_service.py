"""`GetQuestionService`/`ListQuestionsService` — read-only query
services, the same shape `app.modules.community_posts.application
.services.post_query_service` establishes for its own analogous pair.

`GetQuestionService.get_by_id`/`get_by_slug` are the one read path in
this module that enforces `QuestionVisibility` (see `_authorization
.ensure_can_view`'s own docstring) — every other read (`ListQuestionsService`,
the `Browse*Questions` services) is the management/moderator-facing view
or is already restricted to `PUBLISHED`/`CLOSED` questions by
`browse_feed()` itself.
"""

from uuid import UUID

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_questions.application.dto import (
    CommunityQuestionSummaryDTO,
    ListQuestionsInput,
    ListQuestionsOutput,
)
from app.modules.community_questions.application.services._authorization import ensure_can_view
from app.modules.community_questions.application.services._summary_mappers import (
    question_to_summary,
)
from app.modules.community_questions.domain.repositories import CommunityQuestionRepository


class GetQuestionService:
    def __init__(
        self,
        *,
        question_repository: CommunityQuestionRepository,
        community_query_port: CommunityQueryPort,
    ) -> None:
        self._questions = question_repository
        self._communities = community_query_port

    async def get_by_id(
        self, question_id: UUID, *, acting_user_id: UUID | None = None
    ) -> CommunityQuestionSummaryDTO | None:
        question = await self._questions.get_by_id(question_id)
        if question is None:
            return None

        member = (
            await self._communities.get_membership(question.community_id, acting_user_id)
            if acting_user_id is not None
            else None
        )
        ensure_can_view(question, member, user_id=acting_user_id)

        return question_to_summary(question)

    async def get_by_slug(
        self, community_id: UUID, slug: str, *, acting_user_id: UUID | None = None
    ) -> CommunityQuestionSummaryDTO | None:
        question = await self._questions.get_by_slug(community_id, slug)
        if question is None:
            return None

        member = (
            await self._communities.get_membership(question.community_id, acting_user_id)
            if acting_user_id is not None
            else None
        )
        ensure_can_view(question, member, user_id=acting_user_id)

        return question_to_summary(question)


class ListQuestionsService:
    def __init__(self, *, question_repository: CommunityQuestionRepository) -> None:
        self._questions = question_repository

    async def list_questions(self, input_dto: ListQuestionsInput) -> ListQuestionsOutput:
        questions, total = await self._questions.search(
            organization_id=input_dto.organization_id,
            community_id=input_dto.community_id,
            topic_id=input_dto.topic_id,
            author_id=input_dto.author_id,
            question_type=input_dto.question_type,
            status=input_dto.status,
            visibility=input_dto.visibility,
            pinned_only=input_dto.pinned_only,
            featured_only=input_dto.featured_only,
            created_from=input_dto.created_from,
            created_to=input_dto.created_to,
            query=input_dto.query,
            include_deleted=input_dto.include_deleted,
            sort_by=input_dto.sort_by,
            sort_order=input_dto.sort_order,  # type: ignore[arg-type]
            offset=input_dto.offset,
            limit=input_dto.limit,
        )
        return ListQuestionsOutput(
            items=tuple(question_to_summary(q) for q in questions), total=total
        )
