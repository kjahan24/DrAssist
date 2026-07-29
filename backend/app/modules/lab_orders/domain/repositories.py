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
from uuid import UUID

from app.modules.lab_orders.domain.entities import LabOrder, LabOrderItem


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
    async def add(self, lab_order: LabOrder) -> None: ...


class LabOrderItemRepository(ABC):
    @abstractmethod
    async def get_by_id(self, lab_order_item_id: UUID) -> LabOrderItem | None: ...

    @abstractmethod
    async def list_by_lab_order(self, lab_order_id: UUID) -> list[LabOrderItem]: ...

    @abstractmethod
    async def add(self, item: LabOrderItem) -> None: ...
