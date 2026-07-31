"""The Patient module's public port — the only contract another module may
depend on. See `docs/backend-architecture/03_module_architecture.md`
(Patient) and `10_module_communication.md`.

Never import from `app.modules.patient.domain`, `.application` (beyond
this package), or `.infrastructure` from outside this module — this file
and `dto.py` are the entire allowed surface today.

`list_allergies_for_patient`/`list_medical_conditions_for_patient` were
added by the Personal Health Timeline module: that module lists Allergies
and Medical Conditions as two of its required event sources, and the
read logic already existed end-to-end (`PatientAllergyQueryService
.list_allergies_for_patient`/`PatientMedicalConditionQueryService
.list_conditions_for_patient` in `application/services
/patient_sub_resource_query_service.py`, built by the earlier REST APIs
task) — it was simply never exposed past the `public/` boundary, since no
prior consumer needed it. This is a pure exposure gap: no new business
logic, no schema change, no behavior change for any existing caller of
this port.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.patient.public.dto import (
    PatientAllergySummaryDTO,
    PatientMedicalConditionSummaryDTO,
    PatientSummaryDTO,
)


class PatientQueryPort(ABC):
    @abstractmethod
    async def patient_exists(self, patient_id: UUID) -> bool: ...

    @abstractmethod
    async def is_active(self, patient_id: UUID) -> bool: ...

    @abstractmethod
    async def get_patient_summary(self, patient_id: UUID) -> PatientSummaryDTO | None: ...

    @abstractmethod
    async def list_allergies_for_patient(
        self, patient_id: UUID
    ) -> list[PatientAllergySummaryDTO]: ...

    @abstractmethod
    async def list_medical_conditions_for_patient(
        self, patient_id: UUID
    ) -> list[PatientMedicalConditionSummaryDTO]: ...
