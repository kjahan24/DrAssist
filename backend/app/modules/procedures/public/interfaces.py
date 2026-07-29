"""The Procedures module's public port — the only contract another
module may depend on. See
`docs/backend-architecture/03_module_architecture.md` (Procedures) and
`10_module_communication.md`.

Never import from `app.modules.procedures.domain`, `.application`
(beyond this package), or `.infrastructure` from outside this module —
this file and `dto.py` are the entire allowed surface today. Future
modules that need to know a visit's recorded procedures (Clinical Notes,
SOAP Notes, Billing, ...) are expected to depend on this port, the same
way this module itself depends on `VisitQueryPort`.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.procedures.public.dto import ProcedureSummaryDTO


class ProcedureQueryPort(ABC):
    @abstractmethod
    async def procedure_exists(self, procedure_id: UUID) -> bool: ...

    @abstractmethod
    async def list_procedures_for_visit(self, visit_id: UUID) -> list[ProcedureSummaryDTO]: ...
