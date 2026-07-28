"""Repository interface for the `Patient` aggregate, expressed in domain
vocabulary only (no session, no SQL). Concrete implementation lives in
`app.modules.patient.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

No `update()` method: a repository returns the actual aggregate object,
the caller mutates it via its own methods, and the Unit of Work's
`commit()` persists the change through SQLAlchemy's session-level change
tracking.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.patient.domain.entities import Patient


class PatientRepository(ABC):
    @abstractmethod
    async def get_by_id(self, patient_id: UUID) -> Patient | None: ...

    @abstractmethod
    async def get_by_patient_number(
        self, *, organization_id: UUID, patient_number: str
    ) -> Patient | None: ...

    @abstractmethod
    async def list_by_organization(
        self, organization_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[Patient]: ...

    @abstractmethod
    async def add(self, patient: Patient) -> None: ...
