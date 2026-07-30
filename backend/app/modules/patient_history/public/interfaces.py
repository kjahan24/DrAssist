"""The Patient History module's public port — the only contract another
module may depend on. See
`docs/backend-architecture/03_module_architecture.md` and
`10_module_communication.md`.

Never import from `app.modules.patient_history.domain`, `.application`
(beyond this package), or `.infrastructure` from outside this module —
this file, `dto.py`, and `enums.py` are the entire allowed surface
today. This port is the contract every future longitudinal-EMR consumer
(Timeline View, Longitudinal EMR, FHIR Bundle, FHIR Patient, FHIR
Encounter, FHIR Composition, Population Analytics, AI Medical Timeline,
Patient Portal, Mobile App) is expected to depend on to read a patient's
permanent, approved medical record — the same shape
`app.modules.doctor_review.public.interfaces.DoctorReviewQueryPort`
already establishes for its own place under `ClinicalNote`.

There is no `is_editable` here: "History records are immutable" is
unconditionally true for every row, so a method that always returns
`False` would carry no information — see
`application/services/patient_history_query_service.py`.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.patient_history.public.dto import PatientHistorySummaryDTO
from app.modules.patient_history.public.enums import ReferenceType


class PatientHistoryQueryPort(ABC):
    @abstractmethod
    async def patient_history_exists(self, patient_history_id: UUID) -> bool: ...

    @abstractmethod
    async def get_patient_history_summary(
        self, patient_history_id: UUID
    ) -> PatientHistorySummaryDTO | None: ...

    @abstractmethod
    async def get_by_reference(
        self, reference_type: ReferenceType, reference_id: UUID
    ) -> PatientHistorySummaryDTO | None: ...

    @abstractmethod
    async def list_patient_history_for_patient(
        self, patient_id: UUID
    ) -> list[PatientHistorySummaryDTO]: ...

    @abstractmethod
    async def list_patient_history_for_visit(
        self, visit_id: UUID
    ) -> list[PatientHistorySummaryDTO]: ...
