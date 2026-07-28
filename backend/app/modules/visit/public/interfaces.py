"""The Visit module's public port — the only contract another module may
depend on. See `docs/backend-architecture/03_module_architecture.md`
(Visit) and `10_module_communication.md`.

Never import from `app.modules.visit.domain`, `.application` (beyond
this package), or `.infrastructure` from outside this module — this file
and `dto.py` are the entire allowed surface today. Future modules that
attach child records to a visit (Vital Signs, Diagnosis, Chief
Complaints, ...) are expected to depend on this port to confirm a visit
exists before attaching to it, the same way `PatientAllergy.verified_by`
etc. depend on `DoctorQueryPort`.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.visit.public.dto import VisitSummaryDTO


class VisitQueryPort(ABC):
    @abstractmethod
    async def visit_exists(self, visit_id: UUID) -> bool: ...

    @abstractmethod
    async def is_active(self, visit_id: UUID) -> bool: ...

    @abstractmethod
    async def get_visit_summary(self, visit_id: UUID) -> VisitSummaryDTO | None: ...
