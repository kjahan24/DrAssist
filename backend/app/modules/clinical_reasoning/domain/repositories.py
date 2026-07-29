"""Repository interface for the `ClinicalReasoning` aggregate, expressed
in domain vocabulary only (no session, no SQL). Concrete implementation
lives in `app.modules.clinical_reasoning.infrastructure.repositories`.
See `docs/backend-architecture/04_repository_and_service_patterns.md`.

No `update()` method: a repository returns the actual aggregate object,
the caller mutates it via its own methods, and the Unit of Work's
`commit()` persists the change through SQLAlchemy's session-level change
tracking.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.clinical_reasoning.domain.entities import ClinicalReasoning


class ClinicalReasoningRepository(ABC):
    @abstractmethod
    async def get_by_id(self, clinical_reasoning_id: UUID) -> ClinicalReasoning | None: ...

    @abstractmethod
    async def list_by_clinical_note(self, clinical_note_id: UUID) -> list[ClinicalReasoning]: ...

    @abstractmethod
    async def list_by_patient(self, patient_id: UUID) -> list[ClinicalReasoning]: ...

    @abstractmethod
    async def add(self, reasoning: ClinicalReasoning) -> None: ...
