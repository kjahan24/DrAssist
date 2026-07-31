"""Read-only queries against `Appointment`.

Backs the module's public `AppointmentQueryPort` — the one
implementation, per
`docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).

`list_appointments_for_patient`/`list_appointments_for_doctor` are the
two natural parent axes `Appointment` has — the same shape every prior
module's query service exposes for each of its own real FK parents.
Deliberately does *not* add a date-range or "today's schedule" query:
that is squarely Schedule/Availability/Calendar territory, explicitly out
of scope for this task — see `container.py`'s scope note.
"""

from collections.abc import Sequence
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from app.modules.appointment.application.dto import AppointmentSummaryDTO
from app.modules.appointment.domain.entities import Appointment
from app.modules.appointment.domain.enums import AppointmentStatus
from app.modules.appointment.domain.repositories import AppointmentRepository

_NOT_EDITABLE_STATUSES = frozenset({AppointmentStatus.COMPLETED, AppointmentStatus.NO_SHOW})


class AppointmentQueryService:
    def __init__(self, *, appointment_repository: AppointmentRepository) -> None:
        self._appointments = appointment_repository

    async def appointment_exists(self, appointment_id: UUID) -> bool:
        return await self._appointments.get_by_id(appointment_id) is not None

    async def is_editable(self, appointment_id: UUID) -> bool:
        appointment = await self._appointments.get_by_id(appointment_id)
        return appointment is not None and appointment.status not in _NOT_EDITABLE_STATUSES

    async def get_appointment_summary(self, appointment_id: UUID) -> AppointmentSummaryDTO | None:
        appointment = await self._appointments.get_by_id(appointment_id)
        return _to_summary(appointment) if appointment is not None else None

    async def get_by_appointment_number(
        self, appointment_number: str
    ) -> AppointmentSummaryDTO | None:
        appointment = await self._appointments.get_by_appointment_number(appointment_number)
        return _to_summary(appointment) if appointment is not None else None

    async def list_appointments_for_patient(self, patient_id: UUID) -> list[AppointmentSummaryDTO]:
        appointments = await self._appointments.list_by_patient(patient_id)
        return [_to_summary(appointment) for appointment in appointments]

    async def list_appointments_for_doctor(self, doctor_id: UUID) -> list[AppointmentSummaryDTO]:
        appointments = await self._appointments.list_by_doctor(doctor_id)
        return [_to_summary(appointment) for appointment in appointments]

    async def search_appointments(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        statuses: Sequence[AppointmentStatus] | None = None,
        patient_id: UUID | None = None,
        doctor_id: UUID | None = None,
        appointment_date_from: date | None = None,
        appointment_date_to: date | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "appointment_date",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[AppointmentSummaryDTO], int]:
        """Search & Filtering module — see `AppointmentRepository.search`'s
        docstring for filter/sort/pagination semantics."""
        appointments, total = await self._appointments.search(
            organization_id=organization_id,
            query=query,
            statuses=statuses,
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_date_from=appointment_date_from,
            appointment_date_to=appointment_date_to,
            created_from=created_from,
            created_to=created_to,
            updated_from=updated_from,
            updated_to=updated_to,
            include_deleted=include_deleted,
            sort_by=sort_by,
            sort_order=sort_order,
            offset=offset,
            limit=limit,
        )
        return [_to_summary(appointment) for appointment in appointments], total


def _to_summary(appointment: Appointment) -> AppointmentSummaryDTO:
    return AppointmentSummaryDTO(
        appointment_id=appointment.id,
        organization_id=appointment.organization_id,
        patient_id=appointment.patient_id,
        doctor_id=appointment.doctor_id,
        appointment_number=appointment.appointment_number,
        appointment_date=appointment.appointment_date,
        start_time=appointment.start_time,
        end_time=appointment.end_time,
        appointment_type=appointment.appointment_type,
        status=appointment.status,
        reason_for_visit=appointment.reason_for_visit,
        notes=appointment.notes,
        booked_by_user_id=appointment.booked_by_user_id,
        visit_id=appointment.visit_id,
        checked_in_at=appointment.checked_in_at,
        completed_at=appointment.completed_at,
        cancelled_at=appointment.cancelled_at,
    )
