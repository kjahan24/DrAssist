"""The Doctor module's public port — the only contract another module may
depend on. See `docs/backend-architecture/03_module_architecture.md`
(Doctor) and `10_module_communication.md`.

Never import from `app.modules.doctor.domain`, `.application` (beyond
this package), or `.infrastructure` from outside this module — this file
and `dto.py` are the entire allowed surface today.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.doctor.public.dto import DoctorSummaryDTO


class DoctorQueryPort(ABC):
    @abstractmethod
    async def doctor_exists(self, doctor_id: UUID) -> bool: ...

    @abstractmethod
    async def is_active(self, doctor_id: UUID) -> bool: ...

    @abstractmethod
    async def get_doctor_summary(self, doctor_id: UUID) -> DoctorSummaryDTO | None: ...
