"""Repository interfaces for the `LabOrder`/`LabOrderItem` aggregates,
expressed in domain vocabulary only (no session, no SQL). Concrete
implementations live in `app.modules.lab_orders.infrastructure
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

from app.modules.lab_orders.domain.entities import LabOrder, LabOrderItem
from app.modules.lab_orders.domain.enums import LabOrderStatus, Priority


class LabOrderRepository(ABC):
    @abstractmethod
    async def get_by_id(self, lab_order_id: UUID) -> LabOrder | None: ...

    @abstractmethod
    async def get_by_order_number(self, order_number: str) -> LabOrder | None: ...

    @abstractmethod
    async def list_by_clinical_note(self, clinical_note_id: UUID) -> list[LabOrder]: ...

    @abstractmethod
    async def list_by_patient(self, patient_id: UUID) -> list[LabOrder]: ...

    @abstractmethod
    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        statuses: Sequence[LabOrderStatus] | None = None,
        priorities: Sequence[Priority] | None = None,
        patient_id: UUID | None = None,
        doctor_id: UUID | None = None,
        visit_id: UUID | None = None,
        clinical_note_id: UUID | None = None,
        ordered_from: datetime | None = None,
        ordered_to: datetime | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "ordered_at",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[LabOrder], int]:
        """Search & Filtering module: organization-scoped search over lab
        orders — `query` matches `order_number` (partial) and
        `clinical_information`/`notes` (full-text); test names live on
        `LabOrderItem`, not here (see
        `LabOrderItemRepository.list_by_lab_orders` for how the query
        service avoids N+1 when embedding items into search results).
        Returns `(page_of_lab_orders, total_matching_count)`."""
        ...

    @abstractmethod
    async def add(self, lab_order: LabOrder) -> None: ...


class LabOrderItemRepository(ABC):
    @abstractmethod
    async def get_by_id(self, lab_order_item_id: UUID) -> LabOrderItem | None: ...

    @abstractmethod
    async def list_by_lab_order(self, lab_order_id: UUID) -> list[LabOrderItem]: ...

    @abstractmethod
    async def list_by_lab_orders(self, lab_order_ids: Sequence[UUID]) -> list[LabOrderItem]:
        """Search & Filtering module: batch variant of `list_by_lab_order`
        — see `PrescriptionItemRepository.list_by_prescriptions`'s
        docstring for the identical N+1-avoidance rationale."""
        ...

    @abstractmethod
    async def add(self, item: LabOrderItem) -> None: ...
