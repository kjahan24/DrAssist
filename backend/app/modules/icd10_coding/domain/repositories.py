"""Repository interface for the `ICD10Coding` aggregate, expressed in
domain vocabulary only (no session, no SQL). Concrete implementation
lives in `app.modules.icd10_coding.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

No `update()` method: a repository returns the actual aggregate object,
the caller mutates it via its own methods, and the Unit of Work's
`commit()` persists the change through SQLAlchemy's session-level change
tracking.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.icd10_coding.domain.entities import ICD10Coding


class ICD10CodingRepository(ABC):
    @abstractmethod
    async def get_by_id(self, icd10_coding_id: UUID) -> ICD10Coding | None: ...

    @abstractmethod
    async def get_primary_for_clinical_note(self, clinical_note_id: UUID) -> ICD10Coding | None: ...

    @abstractmethod
    async def list_by_clinical_note(self, clinical_note_id: UUID) -> list[ICD10Coding]: ...

    @abstractmethod
    async def list_by_patient(self, patient_id: UUID) -> list[ICD10Coding]: ...

    @abstractmethod
    async def add(self, coding: ICD10Coding) -> None: ...
