"""The Differential Diagnosis module's public port — the only contract
another module may depend on. See
`docs/backend-architecture/03_module_architecture.md` and
`10_module_communication.md`.

Never import from `app.modules.differential_diagnosis.domain`,
`.application` (beyond this package), or `.infrastructure` from outside
this module — this file and `dto.py` are the entire allowed surface
today. This port is the contract every future diagnosis-aware module
(ICD-10 Coding, SNOMED CT, AI Clinical Decision Support, Explainable AI,
Evidence-based Medicine Engine, Doctor Review Dashboard, Clinical
Timeline) is expected to depend on to read a patient's recorded
differential diagnoses — the same shape
`app.modules.clinical_reasoning.public.interfaces.ClinicalReasoningQueryPort`
already establishes for its own one-to-many place under `ClinicalNote`.
`is_editable` is what every one of those future consumers is expected to
check before writing to a diagnosis record.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.differential_diagnosis.public.dto import DifferentialDiagnosisSummaryDTO


class DifferentialDiagnosisQueryPort(ABC):
    @abstractmethod
    async def differential_diagnosis_exists(self, differential_diagnosis_id: UUID) -> bool: ...

    @abstractmethod
    async def is_editable(self, differential_diagnosis_id: UUID) -> bool: ...

    @abstractmethod
    async def get_differential_diagnosis_summary(
        self, differential_diagnosis_id: UUID
    ) -> DifferentialDiagnosisSummaryDTO | None: ...

    @abstractmethod
    async def list_differential_diagnoses_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> list[DifferentialDiagnosisSummaryDTO]: ...

    @abstractmethod
    async def list_differential_diagnoses_for_patient(
        self, patient_id: UUID
    ) -> list[DifferentialDiagnosisSummaryDTO]: ...
