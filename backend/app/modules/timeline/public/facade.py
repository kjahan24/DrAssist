"""`TimelineFacade` — the one concrete implementation of
`TimelineQueryPort`. Constructed per-request by
`app.modules.timeline.container.build_timeline_facade`, bound to that
request's `AsyncSession`.
"""

from typing import Literal
from uuid import UUID

from app.modules.timeline.application.services.timeline_query_service import (
    TimelineQueryService,
)
from app.modules.timeline.public.dto import TimelineFilterInput, TimelinePageDTO
from app.modules.timeline.public.interfaces import TimelineQueryPort


class TimelineFacade(TimelineQueryPort):
    def __init__(self, *, query_service: TimelineQueryService) -> None:
        self._query_service = query_service

    async def get_patient_timeline(
        self,
        patient_id: UUID,
        *,
        filters: TimelineFilterInput,
        offset: int = 0,
        limit: int = 20,
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> TimelinePageDTO:
        return await self._query_service.get_patient_timeline(
            patient_id, filters=filters, offset=offset, limit=limit, sort_order=sort_order
        )
