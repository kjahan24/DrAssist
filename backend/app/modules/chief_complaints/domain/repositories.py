"""Repository interface for the `VisitChiefComplaint` aggregate, expressed
in domain vocabulary only (no session, no SQL). Concrete implementation
lives in `app.modules.chief_complaints.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

No `update()` method: a repository returns the actual aggregate object,
the caller mutates it via its own methods, and the Unit of Work's
`commit()` persists the change through SQLAlchemy's session-level change
tracking.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.chief_complaints.domain.entities import VisitChiefComplaint


class VisitChiefComplaintRepository(ABC):
    @abstractmethod
    async def get_by_id(self, chief_complaint_id: UUID) -> VisitChiefComplaint | None: ...

    @abstractmethod
    async def get_by_visit_and_sequence(
        self, *, visit_id: UUID, sequence_number: int
    ) -> VisitChiefComplaint | None: ...

    @abstractmethod
    async def list_by_visit(self, visit_id: UUID) -> list[VisitChiefComplaint]: ...

    @abstractmethod
    async def add(self, chief_complaint: VisitChiefComplaint) -> None: ...
