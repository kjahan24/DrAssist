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
from collections.abc import Sequence
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.clinical_notes.domain.entities import ClinicalNote
from app.modules.clinical_notes.domain.enums import ClinicalNoteStatus


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
    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        statuses: Sequence[ClinicalNoteStatus] | None = None,
        patient_id: UUID | None = None,
        doctor_id: UUID | None = None,
        visit_id: UUID | None = None,
        encounter_from: datetime | None = None,
        encounter_to: datetime | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "encounter_datetime",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[ClinicalNote], int]:
        """Search & Filtering module: organization-scoped search over
        clinical notes — `query` combines full-text search over the note's
        five free-text summary fields with a partial match on
        `note_number`; `patient_id`/`doctor_id`/`visit_id` are exact-match
        UUID filters; `encounter_from`/`_to` filters the clinical
        `encounter_datetime`, separate from the generic audit timestamps.
        Returns `(page_of_notes, total_matching_count)`."""
        ...

    @abstractmethod
    async def add(self, clinical_note: ClinicalNote) -> None: ...
