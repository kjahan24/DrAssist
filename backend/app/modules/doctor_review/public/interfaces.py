"""The Doctor Review module's public port — the only contract another
module may depend on. See
`docs/backend-architecture/03_module_architecture.md` and
`10_module_communication.md`.

Never import from `app.modules.doctor_review.domain`, `.application`
(beyond this package), or `.infrastructure` from outside this module —
this file and `dto.py` are the entire allowed surface today. This port
is the contract every future review-aware module (Electronic Signature,
Multi-stage Approval, Quality Assurance Review, Clinical Audit, FHIR
Provenance, FHIR Composition, AI Clinical Copilot, Medical Legal Audit,
Hospital Review Committee) is expected to depend on to read a clinical
encounter's physician review — the same shape
`app.modules.icd10_coding.public.interfaces.ICD10CodingQueryPort`
already establishes for its own place under `ClinicalNote`. `is_editable`
is what every one of those future consumers is expected to check before
writing to, or building on top of, a review record; other prior modules
(`ClinicalNote`, `SOAPNote`, `Prescription`, `LabOrder`, `LabResult`,
`ClinicalReasoning`, `DifferentialDiagnosis`, `ICD10Coding`) are *not*
wired to consume this port in this task — see `container.py`'s scope
note for why.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.doctor_review.public.dto import DoctorReviewSummaryDTO


class DoctorReviewQueryPort(ABC):
    @abstractmethod
    async def doctor_review_exists(self, doctor_review_id: UUID) -> bool: ...

    @abstractmethod
    async def is_editable(self, doctor_review_id: UUID) -> bool: ...

    @abstractmethod
    async def get_doctor_review_summary(
        self, doctor_review_id: UUID
    ) -> DoctorReviewSummaryDTO | None: ...

    @abstractmethod
    async def get_doctor_review_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> DoctorReviewSummaryDTO | None: ...

    @abstractmethod
    async def list_doctor_reviews_for_patient(
        self, patient_id: UUID
    ) -> list[DoctorReviewSummaryDTO]: ...
