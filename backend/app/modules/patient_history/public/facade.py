"""`PatientHistoryFacade` — the one concrete implementation of
`PatientHistoryQueryPort`. Constructed per-request by
`app.modules.patient_history.container.build_patient_history_facade`,
bound to that request's `AsyncSession`.
"""

from uuid import UUID

from app.modules.patient_history.application.services.patient_history_query_service import (
    PatientHistoryQueryService,
)
from app.modules.patient_history.public.dto import PatientHistorySummaryDTO
from app.modules.patient_history.public.enums import ReferenceType
from app.modules.patient_history.public.interfaces import PatientHistoryQueryPort


class PatientHistoryFacade(PatientHistoryQueryPort):
    def __init__(self, *, query_service: PatientHistoryQueryService) -> None:
        self._query_service = query_service

    async def patient_history_exists(self, patient_history_id: UUID) -> bool:
        return await self._query_service.patient_history_exists(patient_history_id)

    async def get_patient_history_summary(
        self, patient_history_id: UUID
    ) -> PatientHistorySummaryDTO | None:
        return await self._query_service.get_patient_history_summary(patient_history_id)

    async def get_by_reference(
        self, reference_type: ReferenceType, reference_id: UUID
    ) -> PatientHistorySummaryDTO | None:
        return await self._query_service.get_by_reference(reference_type, reference_id)

    async def list_patient_history_for_patient(
        self, patient_id: UUID
    ) -> list[PatientHistorySummaryDTO]:
        return await self._query_service.list_patient_history_for_patient(patient_id)

    async def list_patient_history_for_visit(
        self, visit_id: UUID
    ) -> list[PatientHistorySummaryDTO]:
        return await self._query_service.list_patient_history_for_visit(visit_id)
