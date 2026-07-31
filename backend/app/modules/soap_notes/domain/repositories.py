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
from collections.abc import Sequence
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.soap_notes.domain.entities import SOAPNote


class SOAPNoteRepository(ABC):
    @abstractmethod
    async def get_by_id(self, soap_note_id: UUID) -> SOAPNote | None: ...

    @abstractmethod
    async def get_by_clinical_note_id(self, clinical_note_id: UUID) -> SOAPNote | None: ...

    @abstractmethod
    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        patient_id: UUID | None = None,
        doctor_id: UUID | None = None,
        visit_id: UUID | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[SOAPNote], int]:
        """Search & Filtering module: organization-scoped search over SOAP
        notes — the module has no prior `list_*` method at all (it's a
        strict 1:1 with `ClinicalNote`, previously only looked up by
        `clinical_note_id`), so this is also the module's first way to
        find SOAP notes across a patient/doctor/visit. `query` is a
        full-text match across all seven free-text fields (no identifier-
        style column exists here to partial-match against, unlike most
        other modules). Returns `(page_of_soap_notes,
        total_matching_count)`."""
        ...

    @abstractmethod
    async def add(self, soap_note: SOAPNote) -> None: ...
