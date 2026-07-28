"""Repository interface for the `VisitVitalSigns` aggregate, expressed in
domain vocabulary only (no session, no SQL). Concrete implementation lives
in `app.modules.vital_signs.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

No `update()` method: a repository returns the actual aggregate object,
the caller mutates it via its own methods, and the Unit of Work's
`commit()` persists the change through SQLAlchemy's session-level change
tracking.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.vital_signs.domain.entities import VisitVitalSigns


class VisitVitalSignsRepository(ABC):
    @abstractmethod
    async def get_by_id(self, vital_signs_id: UUID) -> VisitVitalSigns | None: ...

    @abstractmethod
    async def get_by_visit_id(self, visit_id: UUID) -> VisitVitalSigns | None: ...

    @abstractmethod
    async def add(self, vital_signs: VisitVitalSigns) -> None: ...
