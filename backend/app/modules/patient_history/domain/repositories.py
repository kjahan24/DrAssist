"""Repository interface for the `PatientHistory` aggregate, expressed in
domain vocabulary only (no session, no SQL). Concrete implementation
lives in `app.modules.patient_history.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

No `update()` method — the same reason every other repository in this
codebase lacks one (a repository returns the actual aggregate object and
the Unit of Work persists mutations through SQLAlchemy's session-level
change tracking), made doubly true here since `PatientHistory` itself
has no mutator to call in the first place.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.patient_history.domain.entities import PatientHistory
from app.modules.patient_history.domain.enums import ReferenceType


class PatientHistoryRepository(ABC):
    @abstractmethod
    async def get_by_id(self, patient_history_id: UUID) -> PatientHistory | None: ...

    @abstractmethod
    async def get_by_reference(
        self, reference_type: ReferenceType, reference_id: UUID
    ) -> PatientHistory | None: ...

    @abstractmethod
    async def list_by_patient(self, patient_id: UUID) -> list[PatientHistory]: ...

    @abstractmethod
    async def list_by_visit(self, visit_id: UUID) -> list[PatientHistory]: ...

    @abstractmethod
    async def add(self, history: PatientHistory) -> None: ...
