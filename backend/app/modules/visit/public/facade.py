"""`VisitFacade` — the one concrete implementation of `VisitQueryPort`.
Constructed per-request by
`app.modules.visit.container.build_visit_facade`, bound to that request's
`AsyncSession`.
"""

from uuid import UUID

from app.modules.visit.application.services.patient_visit_query_service import (
    PatientVisitQueryService,
)
from app.modules.visit.public.dto import VisitSummaryDTO
from app.modules.visit.public.interfaces import VisitQueryPort


class VisitFacade(VisitQueryPort):
    def __init__(self, *, query_service: PatientVisitQueryService) -> None:
        self._query_service = query_service

    async def visit_exists(self, visit_id: UUID) -> bool:
        return await self._query_service.visit_exists(visit_id)

    async def is_active(self, visit_id: UUID) -> bool:
        return await self._query_service.is_active(visit_id)

    async def get_visit_summary(self, visit_id: UUID) -> VisitSummaryDTO | None:
        return await self._query_service.get_visit_summary(visit_id)

    async def list_visits_for_patient(self, patient_id: UUID) -> list[VisitSummaryDTO]:
        return await self._query_service.list_visits_for_patient(patient_id)
