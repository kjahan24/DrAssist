"""`PatientFacade` — the one concrete implementation of `PatientQueryPort`.
Constructed per-request by
`app.modules.patient.container.build_patient_facade`, bound to that
request's `AsyncSession`.
"""

from uuid import UUID

from app.modules.patient.application.services.patient_query_service import PatientQueryService
from app.modules.patient.public.dto import PatientSummaryDTO
from app.modules.patient.public.interfaces import PatientQueryPort


class PatientFacade(PatientQueryPort):
    def __init__(self, *, query_service: PatientQueryService) -> None:
        self._query_service = query_service

    async def patient_exists(self, patient_id: UUID) -> bool:
        return await self._query_service.patient_exists(patient_id)

    async def is_active(self, patient_id: UUID) -> bool:
        return await self._query_service.is_active(patient_id)

    async def get_patient_summary(self, patient_id: UUID) -> PatientSummaryDTO | None:
        return await self._query_service.get_patient_summary(patient_id)
