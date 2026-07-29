"""Repository interface for the `SOAPNote` aggregate, expressed in domain
vocabulary only (no session, no SQL). Concrete implementation lives in
`app.modules.soap_notes.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

No `update()` method: a repository returns the actual aggregate object,
the caller mutates it via its own methods, and the Unit of Work's
`commit()` persists the change through SQLAlchemy's session-level change
tracking.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.soap_notes.domain.entities import SOAPNote


class SOAPNoteRepository(ABC):
    @abstractmethod
    async def get_by_id(self, soap_note_id: UUID) -> SOAPNote | None: ...

    @abstractmethod
    async def get_by_clinical_note_id(self, clinical_note_id: UUID) -> SOAPNote | None: ...

    @abstractmethod
    async def add(self, soap_note: SOAPNote) -> None: ...
