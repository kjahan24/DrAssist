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
from uuid import UUID

from app.modules.appointment.domain.entities import Appointment


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
    async def add(self, appointment: Appointment) -> None: ...
