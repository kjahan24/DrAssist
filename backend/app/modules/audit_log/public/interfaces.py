"""The Audit Log module's public port — the only contract another module
may depend on. See `docs/backend-architecture/03_module_architecture.md`
and `10_module_communication.md`.

Never import from `app.modules.audit_log.domain`, `.application`
(beyond this package), or `.infrastructure` from outside this module —
this file, `dto.py`, and `enums.py` are the entire allowed surface
today. `docs/backend-architecture/03_module_architecture.md` itself
names Audit's special place in the dependency graph: "Audit is the one
module permitted to subscribe to every domain event published anywhere
in the system... No other module ever depends on Audit's `public/`
interface for its own business operation — Audit is a pure sink, never a
source." This port is read-only (a `<X>QueryPort`, the same shape every
other module's own public port takes) for exactly that reason: writing
an audit entry is a side effect of another module's own business
operation, not a query it depends on, so the write path
(`RecordAuditLog`) is exposed as a plain use-case factory from
`container.py` instead — see that file's own scope note, the same "no
API layer, so container.py builds both the read facade and write-side
use-case factories" shape `app.modules.notification.container` already
establishes.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.audit_log.public.dto import AuditLogSummaryDTO


class AuditLogQueryPort(ABC):
    @abstractmethod
    async def get_by_id(self, audit_log_id: UUID) -> AuditLogSummaryDTO | None: ...

    @abstractmethod
    async def list_for_entity(
        self, *, entity_type: str, entity_id: UUID
    ) -> list[AuditLogSummaryDTO]: ...

    @abstractmethod
    async def list_for_organization(
        self, organization_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[AuditLogSummaryDTO]: ...

    @abstractmethod
    async def list_for_actor(self, actor_user_id: UUID) -> list[AuditLogSummaryDTO]: ...
