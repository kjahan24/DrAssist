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
from uuid import UUID

from app.modules.lab_results.domain.entities import LabResult, LabResultItem


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
    async def add(self, lab_result: LabResult) -> None: ...


class LabResultItemRepository(ABC):
    @abstractmethod
    async def get_by_id(self, lab_result_item_id: UUID) -> LabResultItem | None: ...

    @abstractmethod
    async def list_by_lab_result(self, lab_result_id: UUID) -> list[LabResultItem]: ...

    @abstractmethod
    async def add(self, item: LabResultItem) -> None: ...
