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

`list_visits_for_patient` was added by the Personal Health Timeline
module: that module lists Visits as one of its required event sources,
and no existing path could enumerate "every visit for a patient" at
all — the port previously only supported single-id lookup
(`get_visit_summary`). The read logic already existed one layer down
(`PatientVisitQueryService.list_visits_for_patient`, backed by
`PatientVisitRepository.list_by_patient` — both added by the earlier
REST APIs task for this module's own `GET /visits/patient/{patient_id}`
endpoint) — this is a pure exposure gap, the same shape as the Patient
module's own `list_allergies_for_patient` addition.
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

    @abstractmethod
    async def list_visits_for_patient(self, patient_id: UUID) -> list[VisitSummaryDTO]: ...
