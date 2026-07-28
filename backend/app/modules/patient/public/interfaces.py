"""The Patient module's public port — the only contract another module may
depend on. See `docs/backend-architecture/03_module_architecture.md`
(Patient) and `10_module_communication.md`.

Never import from `app.modules.patient.domain`, `.application` (beyond
this package), or `.infrastructure` from outside this module — this file
and `dto.py` are the entire allowed surface today.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.patient.public.dto import PatientSummaryDTO


class PatientQueryPort(ABC):
    @abstractmethod
    async def patient_exists(self, patient_id: UUID) -> bool: ...

    @abstractmethod
    async def is_active(self, patient_id: UUID) -> bool: ...

    @abstractmethod
    async def get_patient_summary(self, patient_id: UUID) -> PatientSummaryDTO | None: ...
