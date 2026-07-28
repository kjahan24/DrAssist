"""The Vital Signs module's public port — the only contract another
module may depend on. See
`docs/backend-architecture/03_module_architecture.md` (Vital Signs) and
`10_module_communication.md`.

Never import from `app.modules.vital_signs.domain`, `.application`
(beyond this package), or `.infrastructure` from outside this module —
this file and `dto.py` are the entire allowed surface today. Future
modules that need to know whether a visit's vitals have been recorded
(Clinical Notes, SOAP Notes, ...) are expected to depend on this port,
the same way this module itself depends on `VisitQueryPort`.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.vital_signs.public.dto import VitalSignsSummaryDTO


class VitalSignsQueryPort(ABC):
    @abstractmethod
    async def vital_signs_exist_for_visit(self, visit_id: UUID) -> bool: ...

    @abstractmethod
    async def get_vital_signs_summary_for_visit(
        self, visit_id: UUID
    ) -> VitalSignsSummaryDTO | None: ...
