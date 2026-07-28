"""`VitalSignsFacade` — the one concrete implementation of
`VitalSignsQueryPort`. Constructed per-request by
`app.modules.vital_signs.container.build_vital_signs_facade`, bound to
that request's `AsyncSession`.
"""

from uuid import UUID

from app.modules.vital_signs.application.services.vital_signs_query_service import (
    VisitVitalSignsQueryService,
)
from app.modules.vital_signs.public.dto import VitalSignsSummaryDTO
from app.modules.vital_signs.public.interfaces import VitalSignsQueryPort


class VitalSignsFacade(VitalSignsQueryPort):
    def __init__(self, *, query_service: VisitVitalSignsQueryService) -> None:
        self._query_service = query_service

    async def vital_signs_exist_for_visit(self, visit_id: UUID) -> bool:
        return await self._query_service.vital_signs_exist_for_visit(visit_id)

    async def get_vital_signs_summary_for_visit(
        self, visit_id: UUID
    ) -> VitalSignsSummaryDTO | None:
        return await self._query_service.get_vital_signs_summary_for_visit(visit_id)
