"""`LabResultFacade` — the one concrete implementation of
`LabResultQueryPort`. Constructed per-request by
`app.modules.lab_results.container.build_lab_result_facade`, bound to
that request's `AsyncSession`.
"""

from uuid import UUID

from app.modules.lab_results.application.services.lab_result_query_service import (
    LabResultQueryService,
)
from app.modules.lab_results.public.dto import LabResultSummaryDTO
from app.modules.lab_results.public.interfaces import LabResultQueryPort


class LabResultFacade(LabResultQueryPort):
    def __init__(self, *, query_service: LabResultQueryService) -> None:
        self._query_service = query_service

    async def lab_result_exists_for_lab_order(self, lab_order_id: UUID) -> bool:
        return await self._query_service.lab_result_exists_for_lab_order(lab_order_id)

    async def is_editable(self, lab_order_id: UUID) -> bool:
        return await self._query_service.is_editable(lab_order_id)

    async def get_lab_result_summary(self, lab_order_id: UUID) -> LabResultSummaryDTO | None:
        return await self._query_service.get_lab_result_summary(lab_order_id)

    async def list_lab_results_for_patient(self, patient_id: UUID) -> list[LabResultSummaryDTO]:
        return await self._query_service.list_lab_results_for_patient(patient_id)
