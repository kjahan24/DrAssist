"""Repository interfaces for the `LabResult`/`LabResultItem` aggregates,
expressed in domain vocabulary only (no session, no SQL). Concrete
implementations live in `app.modules.lab_results.infrastructure
.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

No `update()` method on either interface: a repository returns the actual
aggregate object, the caller mutates it via its own methods, and the Unit
of Work's `commit()` persists the change through SQLAlchemy's
session-level change tracking.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.lab_results.domain.entities import LabResult, LabResultItem
from app.modules.lab_results.domain.enums import LabResultStatus


class LabResultRepository(ABC):
    @abstractmethod
    async def get_by_id(self, lab_result_id: UUID) -> LabResult | None: ...

    @abstractmethod
    async def get_by_lab_order_id(self, lab_order_id: UUID) -> LabResult | None: ...

    @abstractmethod
    async def get_by_result_number(self, result_number: str) -> LabResult | None: ...

    @abstractmethod
    async def list_by_patient(self, patient_id: UUID) -> list[LabResult]: ...

    @abstractmethod
    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        statuses: Sequence[LabResultStatus] | None = None,
        patient_id: UUID | None = None,
        doctor_id: UUID | None = None,
        visit_id: UUID | None = None,
        lab_order_id: UUID | None = None,
        reported_from: datetime | None = None,
        reported_to: datetime | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "reported_at",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[LabResult], int]:
        """Search & Filtering module: organization-scoped search over lab
        results — `query` matches `result_number` (partial) and
        `laboratory_name`/`comments` (full-text); test values live on
        `LabResultItem`, not here (see
        `LabResultItemRepository.list_by_lab_results` for how the query
        service avoids N+1 when embedding items into search results).
        Returns `(page_of_lab_results, total_matching_count)`."""
        ...

    @abstractmethod
    async def add(self, lab_result: LabResult) -> None: ...


class LabResultItemRepository(ABC):
    @abstractmethod
    async def get_by_id(self, lab_result_item_id: UUID) -> LabResultItem | None: ...

    @abstractmethod
    async def list_by_lab_result(self, lab_result_id: UUID) -> list[LabResultItem]: ...

    @abstractmethod
    async def list_by_lab_results(self, lab_result_ids: Sequence[UUID]) -> list[LabResultItem]:
        """Search & Filtering module: batch variant of
        `list_by_lab_result` — see
        `PrescriptionItemRepository.list_by_prescriptions`'s docstring for
        the identical N+1-avoidance rationale."""
        ...

    @abstractmethod
    async def add(self, item: LabResultItem) -> None: ...
