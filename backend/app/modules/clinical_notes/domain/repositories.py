"""Repository interface for the `ClinicalNote` aggregate, expressed in
domain vocabulary only (no session, no SQL). Concrete implementation
lives in `app.modules.clinical_notes.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

No `update()` method: a repository returns the actual aggregate object,
the caller mutates it via its own methods, and the Unit of Work's
`commit()` persists the change through SQLAlchemy's session-level change
tracking.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.clinical_notes.domain.entities import ClinicalNote


class ClinicalNoteRepository(ABC):
    @abstractmethod
    async def get_by_id(self, clinical_note_id: UUID) -> ClinicalNote | None: ...

    @abstractmethod
    async def get_by_note_number(self, note_number: str) -> ClinicalNote | None: ...

    @abstractmethod
    async def list_by_visit(self, visit_id: UUID) -> list[ClinicalNote]: ...

    @abstractmethod
    async def list_by_patient(self, patient_id: UUID) -> list[ClinicalNote]: ...

    @abstractmethod
    async def add(self, clinical_note: ClinicalNote) -> None: ...
