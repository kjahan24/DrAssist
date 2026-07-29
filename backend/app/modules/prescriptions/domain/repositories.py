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
from uuid import UUID

from app.modules.prescriptions.domain.entities import Prescription, PrescriptionItem


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
    async def add(self, prescription: Prescription) -> None: ...


class PrescriptionItemRepository(ABC):
    @abstractmethod
    async def get_by_id(self, prescription_item_id: UUID) -> PrescriptionItem | None: ...

    @abstractmethod
    async def list_by_prescription(self, prescription_id: UUID) -> list[PrescriptionItem]: ...

    @abstractmethod
    async def add(self, item: PrescriptionItem) -> None: ...
