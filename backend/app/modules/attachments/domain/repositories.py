"""Repository interface for the `VisitAttachment` aggregate, expressed in
domain vocabulary only (no session, no SQL). Concrete implementation
lives in `app.modules.attachments.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

No `update()` method: a repository returns the actual aggregate object,
the caller mutates it via its own methods, and the Unit of Work's
`commit()` persists the change through SQLAlchemy's session-level change
tracking.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.attachments.domain.entities import VisitAttachment
from app.modules.attachments.domain.value_objects import Sha256Checksum


class VisitAttachmentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, attachment_id: UUID) -> VisitAttachment | None: ...

    @abstractmethod
    async def get_by_storage_key(self, storage_key: str) -> VisitAttachment | None: ...

    @abstractmethod
    async def get_by_checksum(self, checksum: Sha256Checksum) -> VisitAttachment | None: ...

    @abstractmethod
    async def list_by_visit(self, visit_id: UUID) -> list[VisitAttachment]: ...

    @abstractmethod
    async def add(self, attachment: VisitAttachment) -> None: ...
