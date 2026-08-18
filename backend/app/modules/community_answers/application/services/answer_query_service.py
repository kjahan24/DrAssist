"""`GetAnswerService`/`ListAnswersService` — read-only query services,
the same shape `app.modules.community_questions.application.services
.question_query_service` establishes for its own analogous pair.

`GetAnswerService.get_by_id` is the one read path in this module that
enforces `AnswerVisibility` (see `_authorization.ensure_can_view`'s own
docstring) — `ListAnswersService`/`SearchAnswersService` are the
management/moderator-facing view, and the cursor feeds
(`ListQuestionAnswersService`/`ListAuthorAnswersService`) are already
restricted to `PUBLISHED` answers by `browse_feed()` itself.
"""

from uuid import UUID

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_answers.application.dto import (
    CommunityAnswerSummaryDTO,
    ListAnswersInput,
    ListAnswersOutput,
)
from app.modules.community_answers.application.services._authorization import ensure_can_view
from app.modules.community_answers.application.services._summary_mappers import answer_to_summary
from app.modules.community_answers.domain.repositories import CommunityAnswerRepository


class GetAnswerService:
    def __init__(
        self,
        *,
        answer_repository: CommunityAnswerRepository,
        community_query_port: CommunityQueryPort,
    ) -> None:
        self._answers = answer_repository
        self._communities = community_query_port

    async def get_by_id(
        self, answer_id: UUID, *, acting_user_id: UUID | None = None
    ) -> CommunityAnswerSummaryDTO | None:
        answer = await self._answers.get_by_id(answer_id)
        if answer is None:
            return None

        member = (
            await self._communities.get_membership(answer.community_id, acting_user_id)
            if acting_user_id is not None
            else None
        )
        ensure_can_view(answer, member, user_id=acting_user_id)

        return answer_to_summary(answer)


class ListAnswersService:
    def __init__(self, *, answer_repository: CommunityAnswerRepository) -> None:
        self._answers = answer_repository

    async def list_answers(self, input_dto: ListAnswersInput) -> ListAnswersOutput:
        answers, total = await self._answers.search(
            organization_id=input_dto.organization_id,
            question_id=input_dto.question_id,
            community_id=input_dto.community_id,
            topic_id=input_dto.topic_id,
            author_id=input_dto.author_id,
            status=input_dto.status,
            visibility=input_dto.visibility,
            best_answer_only=input_dto.best_answer_only,
            featured_only=input_dto.featured_only,
            pinned_only=input_dto.pinned_only,
            created_from=input_dto.created_from,
            created_to=input_dto.created_to,
            query=input_dto.query,
            include_deleted=input_dto.include_deleted,
            sort_by=input_dto.sort_by,
            sort_order=input_dto.sort_order,  # type: ignore[arg-type]
            offset=input_dto.offset,
            limit=input_dto.limit,
        )
        return ListAnswersOutput(items=tuple(answer_to_summary(a) for a in answers), total=total)
