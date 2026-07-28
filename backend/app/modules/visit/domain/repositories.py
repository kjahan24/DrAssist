"""Repository interface for the `PatientVisit` aggregate, expressed in
domain vocabulary only (no session, no SQL). Concrete implementation lives
in `app.modules.visit.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

No `update()` method: a repository returns the actual aggregate object,
the caller mutates it via its own methods, and the Unit of Work's
`commit()` persists the change through SQLAlchemy's session-level change
tracking.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.visit.domain.entities import PatientVisit


class PatientVisitRepository(ABC):
    @abstractmethod
    async def get_by_id(self, visit_id: UUID) -> PatientVisit | None: ...

    @abstractmethod
    async def get_by_visit_number(
        self, *, organization_id: UUID, visit_number: str
    ) -> PatientVisit | None: ...

    @abstractmethod
    async def list_by_patient(self, patient_id: UUID) -> list[PatientVisit]: ...

    @abstractmethod
    async def add(self, visit: PatientVisit) -> None: ...
