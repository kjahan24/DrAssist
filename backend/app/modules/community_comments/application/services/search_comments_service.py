"""`SearchCommentsService` — the general-purpose, cursor-paginated,
full-filter view over comments: every QUERY/PAGINATION filter this
task's own section names (target/author/community/topic/status/parent/
keyword/date range), `query` optional (unlike
`app.modules.community_answers.application.services.search_answers_service
.SearchAnswersService`, whose `query` is mandatory) — this is
deliberate: with `query=None` and e.g. `author_id=<caller>,
status=(DRAFT,)`, this same service also backs a "my drafts" management
view, so there is no separate offset-paginated `ListCommentsService`-
style general list the way `app.modules.community_answers.application
.services.answer_query_service.ListAnswersService` exists for Answers —
see `CommunityCommentRepository.browse`'s own docstring for the full
"one flexible cursor method" reasoning this task's own "Use
deterministic cursor pagination" instruction drives."""

from app.modules.community_comments.application.dto import (
    SearchCommentsInput,
    SearchCommentsOutput,
)
from app.modules.community_comments.application.services._summary_mappers import (
    comment_to_summary,
)
from app.modules.community_comments.domain.repositories import CommunityCommentRepository


class SearchCommentsService:
    def __init__(self, *, comment_repository: CommunityCommentRepository) -> None:
        self._comments = comment_repository

    async def search(self, input_dto: SearchCommentsInput) -> SearchCommentsOutput:
        comments, next_cursor = await self._comments.browse(
            organization_id=input_dto.organization_id,
            target_type=input_dto.target_type,
            target_id=input_dto.target_id,
            community_id=input_dto.community_id,
            topic_id=input_dto.topic_id,
            author_id=input_dto.author_id,
            parent_comment_id=input_dto.parent_comment_id,
            top_level_only=input_dto.top_level_only,
            status=input_dto.status,
            query=input_dto.query,
            created_from=input_dto.created_from,
            created_to=input_dto.created_to,
            include_deleted=input_dto.include_deleted,
            sort_order=input_dto.sort_order,
            cursor=input_dto.cursor,
            limit=input_dto.limit,
        )
        return SearchCommentsOutput(
            items=tuple(comment_to_summary(c) for c in comments), next_cursor=next_cursor
        )
