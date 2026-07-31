"""Repository interfaces for the `Prescription`/`PrescriptionItem`
aggregates, expressed in domain vocabulary only (no session, no SQL).
Concrete implementations live in
`app.modules.prescriptions.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

No `update()` method on either interface: a repository returns the actual
aggregate object, the caller mutates it via its own methods, and the Unit
of Work's `commit()` persists the change through SQLAlchemy's
session-level change tracking.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from app.modules.prescriptions.domain.entities import Prescription, PrescriptionItem
from app.modules.prescriptions.domain.enums import PrescriptionStatus


class PrescriptionRepository(ABC):
    @abstractmethod
    async def get_by_id(self, prescription_id: UUID) -> Prescription | None: ...

    @abstractmethod
    async def get_by_clinical_note_id(self, clinical_note_id: UUID) -> Prescription | None: ...

    @abstractmethod
    async def get_by_prescription_number(self, prescription_number: str) -> Prescription | None: ...

    @abstractmethod
    async def list_by_patient(self, patient_id: UUID) -> list[Prescription]: ...

    @abstractmethod
    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        statuses: Sequence[PrescriptionStatus] | None = None,
        patient_id: UUID | None = None,
        doctor_id: UUID | None = None,
        visit_id: UUID | None = None,
        prescription_date_from: date | None = None,
        prescription_date_to: date | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Prescription], int]:
        """Search & Filtering module: organization-scoped search over
        prescriptions — `query` matches `prescription_number` (partial)
        and `notes` (full-text); medication names live on
        `PrescriptionItem`, not here (see
        `PrescriptionItemRepository.list_by_prescriptions` for how the
        query service avoids N+1 when embedding items into search
        results). Returns `(page_of_prescriptions,
        total_matching_count)`."""
        ...

    @abstractmethod
    async def add(self, prescription: Prescription) -> None: ...


class PrescriptionItemRepository(ABC):
    @abstractmethod
    async def get_by_id(self, prescription_item_id: UUID) -> PrescriptionItem | None: ...

    @abstractmethod
    async def list_by_prescription(self, prescription_id: UUID) -> list[PrescriptionItem]: ...

    @abstractmethod
    async def list_by_prescriptions(
        self, prescription_ids: Sequence[UUID]
    ) -> list[PrescriptionItem]:
        """Search & Filtering module: batch variant of
        `list_by_prescription` — one `WHERE prescription_id IN (...)`
        query for *all* items across a page of prescriptions, instead of
        one query per prescription. Used by
        `PrescriptionQueryService.search_prescriptions` to build each
        result's embedded item list without N+1 queries; the single-id
        `list_by_prescription` stays as-is for existing callers."""
        ...

    @abstractmethod
    async def add(self, item: PrescriptionItem) -> None: ...
