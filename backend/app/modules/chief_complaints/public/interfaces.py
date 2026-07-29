"""The Chief Complaints module's public port — the only contract another
module may depend on. See
`docs/backend-architecture/03_module_architecture.md` (Chief Complaints)
and `10_module_communication.md`.

Never import from `app.modules.chief_complaints.domain`, `.application`
(beyond this package), or `.infrastructure` from outside this module —
this file and `dto.py` are the entire allowed surface today. Future
modules that need to know a visit's recorded complaints (Diagnosis,
Clinical Notes, SOAP Notes, ...) are expected to depend on this port, the
same way this module itself depends on `VisitQueryPort`.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.chief_complaints.public.dto import ChiefComplaintSummaryDTO


class ChiefComplaintQueryPort(ABC):
    @abstractmethod
    async def chief_complaint_exists(self, chief_complaint_id: UUID) -> bool: ...

    @abstractmethod
    async def list_chief_complaints_for_visit(
        self, visit_id: UUID
    ) -> list[ChiefComplaintSummaryDTO]: ...
