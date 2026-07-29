"""Repository interface for the `VisitProcedure` aggregate, expressed in
domain vocabulary only (no session, no SQL). Concrete implementation
lives in `app.modules.procedures.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

No `update()` method: a repository returns the actual aggregate object,
the caller mutates it via its own methods, and the Unit of Work's
`commit()` persists the change through SQLAlchemy's session-level change
tracking.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.procedures.domain.entities import VisitProcedure


class VisitProcedureRepository(ABC):
    @abstractmethod
    async def get_by_id(self, procedure_id: UUID) -> VisitProcedure | None: ...

    @abstractmethod
    async def get_by_visit_and_sequence(
        self, *, visit_id: UUID, sequence_number: int
    ) -> VisitProcedure | None: ...

    @abstractmethod
    async def list_by_visit(self, visit_id: UUID) -> list[VisitProcedure]: ...

    @abstractmethod
    async def add(self, procedure: VisitProcedure) -> None: ...
