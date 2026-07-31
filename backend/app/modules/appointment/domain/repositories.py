"""Repository interface for the `Appointment` aggregate, expressed in
domain vocabulary only (no session, no SQL). Concrete implementation
lives in `app.modules.appointment.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

No `update()` method: a repository returns the actual aggregate object,
the caller mutates it via its own methods, and the Unit of Work's
`commit()` persists the change through SQLAlchemy's session-level change
tracking.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from app.modules.appointment.domain.entities import Appointment
from app.modules.appointment.domain.enums import AppointmentStatus


class AppointmentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, appointment_id: UUID) -> Appointment | None: ...

    @abstractmethod
    async def get_by_appointment_number(self, appointment_number: str) -> Appointment | None: ...

    @abstractmethod
    async def list_by_patient(self, patient_id: UUID) -> list[Appointment]: ...

    @abstractmethod
    async def list_by_doctor(self, doctor_id: UUID) -> list[Appointment]: ...

    @abstractmethod
    async def search(
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
    ) -> tuple[Sequence[Appointment], int]:
        """Search & Filtering module: organization-scoped search over
        appointments — `query` combines full-text search
        (`reason_for_visit`/`notes`) with a partial match on
        `appointment_number`; `patient_id`/`doctor_id` are exact-match UUID
        filters (the "UUID search" requirement); `appointment_date_from`/
        `_to` filters the clinical appointment date, separate from the
        generic `created_at`/`updated_at` audit-timestamp ranges. Returns
        `(page_of_appointments, total_matching_count)`."""
        ...

    @abstractmethod
    async def add(self, appointment: Appointment) -> None: ...
