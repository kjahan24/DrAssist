"""Repository interface for the `MedicalDocument` aggregate, expressed in
domain vocabulary only (no session, no SQL). Concrete implementation lives
in `app.modules.documents.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

No `update()` method: a repository returns the actual aggregate object,
the caller mutates it via its own methods, and the Unit of Work's
`commit()` persists the change through SQLAlchemy's session-level change
tracking.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.documents.domain.entities import MedicalDocument


class MedicalDocumentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, document_id: UUID) -> MedicalDocument | None: ...

    @abstractmethod
    async def get_by_stored_filename(self, stored_filename: str) -> MedicalDocument | None: ...

    @abstractmethod
    async def list_by_patient(self, patient_id: UUID) -> list[MedicalDocument]: ...

    @abstractmethod
    async def list_by_visit(self, visit_id: UUID) -> list[MedicalDocument]: ...

    @abstractmethod
    async def list_by_appointment(self, appointment_id: UUID) -> list[MedicalDocument]: ...

    @abstractmethod
    async def add(self, document: MedicalDocument) -> None: ...
