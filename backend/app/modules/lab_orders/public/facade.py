"""`LabOrderFacade` — the one concrete implementation of
`LabOrderQueryPort`. Constructed per-request by
`app.modules.lab_orders.container.build_lab_order_facade`, bound to that
request's `AsyncSession`.
"""

from uuid import UUID

from app.modules.lab_orders.application.services.lab_order_query_service import (
    LabOrderQueryService,
)
from app.modules.lab_orders.public.dto import LabOrderSummaryDTO
from app.modules.lab_orders.public.interfaces import LabOrderQueryPort


class LabOrderFacade(LabOrderQueryPort):
    def __init__(self, *, query_service: LabOrderQueryService) -> None:
        self._query_service = query_service

    async def lab_order_exists(self, lab_order_id: UUID) -> bool:
        return await self._query_service.lab_order_exists(lab_order_id)

    async def is_editable(self, lab_order_id: UUID) -> bool:
        return await self._query_service.is_editable(lab_order_id)

    async def get_lab_order_summary(self, lab_order_id: UUID) -> LabOrderSummaryDTO | None:
        return await self._query_service.get_lab_order_summary(lab_order_id)

    async def list_lab_orders_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> list[LabOrderSummaryDTO]:
        return await self._query_service.list_lab_orders_for_clinical_note(clinical_note_id)

    async def list_lab_orders_for_patient(self, patient_id: UUID) -> list[LabOrderSummaryDTO]:
        return await self._query_service.list_lab_orders_for_patient(patient_id)
