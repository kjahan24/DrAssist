"""`ChiefComplaintFacade` — the one concrete implementation of
`ChiefComplaintQueryPort`. Constructed per-request by
`app.modules.chief_complaints.container.build_chief_complaint_facade`,
bound to that request's `AsyncSession`.
"""

from uuid import UUID

from app.modules.chief_complaints.application.services.chief_complaint_query_service import (
    VisitChiefComplaintQueryService,
)
from app.modules.chief_complaints.public.dto import ChiefComplaintSummaryDTO
from app.modules.chief_complaints.public.interfaces import ChiefComplaintQueryPort


class ChiefComplaintFacade(ChiefComplaintQueryPort):
    def __init__(self, *, query_service: VisitChiefComplaintQueryService) -> None:
        self._query_service = query_service

    async def chief_complaint_exists(self, chief_complaint_id: UUID) -> bool:
        return await self._query_service.chief_complaint_exists(chief_complaint_id)

    async def list_chief_complaints_for_visit(
        self, visit_id: UUID
    ) -> list[ChiefComplaintSummaryDTO]:
        return await self._query_service.list_chief_complaints_for_visit(visit_id)
