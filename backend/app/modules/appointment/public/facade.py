"""`AppointmentFacade` — the one concrete implementation of
`AppointmentQueryPort`. Constructed per-request by
`app.modules.appointment.container.build_appointment_facade`, bound to
that request's `AsyncSession`.
"""

from uuid import UUID

from app.modules.appointment.application.services.appointment_query_service import (
    AppointmentQueryService,
)
from app.modules.appointment.public.dto import AppointmentSummaryDTO
from app.modules.appointment.public.interfaces import AppointmentQueryPort


class AppointmentFacade(AppointmentQueryPort):
    def __init__(self, *, query_service: AppointmentQueryService) -> None:
        self._query_service = query_service

    async def appointment_exists(self, appointment_id: UUID) -> bool:
        return await self._query_service.appointment_exists(appointment_id)

    async def is_editable(self, appointment_id: UUID) -> bool:
        return await self._query_service.is_editable(appointment_id)

    async def get_appointment_summary(self, appointment_id: UUID) -> AppointmentSummaryDTO | None:
        return await self._query_service.get_appointment_summary(appointment_id)

    async def get_by_appointment_number(
        self, appointment_number: str
    ) -> AppointmentSummaryDTO | None:
        return await self._query_service.get_by_appointment_number(appointment_number)

    async def list_appointments_for_patient(self, patient_id: UUID) -> list[AppointmentSummaryDTO]:
        return await self._query_service.list_appointments_for_patient(patient_id)

    async def list_appointments_for_doctor(self, doctor_id: UUID) -> list[AppointmentSummaryDTO]:
        return await self._query_service.list_appointments_for_doctor(doctor_id)
