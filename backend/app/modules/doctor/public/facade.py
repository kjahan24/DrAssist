"""`DoctorFacade` — the one concrete implementation of `DoctorQueryPort`.
Constructed per-request by `app.modules.doctor.container.build_doctor_facade`,
bound to that request's `AsyncSession`.
"""

from uuid import UUID

from app.modules.doctor.application.services.doctor_query_service import DoctorQueryService
from app.modules.doctor.public.dto import DoctorSummaryDTO
from app.modules.doctor.public.interfaces import DoctorQueryPort


class DoctorFacade(DoctorQueryPort):
    def __init__(self, *, query_service: DoctorQueryService) -> None:
        self._query_service = query_service

    async def doctor_exists(self, doctor_id: UUID) -> bool:
        return await self._query_service.doctor_exists(doctor_id)

    async def is_active(self, doctor_id: UUID) -> bool:
        return await self._query_service.is_active(doctor_id)

    async def get_doctor_summary(self, doctor_id: UUID) -> DoctorSummaryDTO | None:
        return await self._query_service.get_doctor_summary(doctor_id)
