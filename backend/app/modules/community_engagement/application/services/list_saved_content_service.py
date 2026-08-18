"""`ListSavedContentService` — the acting user's own saved Posts/
Questions/Answers, cursor-paginated, optionally filtered to one
`target_type`. There is no "list who saved this" read path (the mirror
image of votes never exposing voters) — saves are always scoped to
`user_id` here, never to `target_id` alone, since a user's own saved
list is private to them; see `vote_query_service.py`'s own docstring for
the identical "no list-by-target read path" reasoning applied to votes.
"""

from app.modules.community_engagement.application.dto import (
    ListSavedContentInput,
    SavedContentFeedOutput,
)
from app.modules.community_engagement.application.services._summary_mappers import (
    saved_content_to_summary,
)
from app.modules.community_engagement.domain.repositories import SavedContentRepository


class ListSavedContentService:
    def __init__(self, *, saved_content_repository: SavedContentRepository) -> None:
        self._saved = saved_content_repository

    async def list_saved(self, input_dto: ListSavedContentInput) -> SavedContentFeedOutput:
        items, next_cursor = await self._saved.list_by_user(
            input_dto.user_id,
            target_type=input_dto.target_type,
            cursor=input_dto.cursor,
            limit=input_dto.limit,
        )
        return SavedContentFeedOutput(
            items=tuple(saved_content_to_summary(s) for s in items), next_cursor=next_cursor
        )
