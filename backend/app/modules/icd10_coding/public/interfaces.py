"""The ICD-10 Coding module's public port — the only contract another
module may depend on. See
`docs/backend-architecture/03_module_architecture.md` and
`10_module_communication.md`.

Never import from `app.modules.icd10_coding.domain`, `.application`
(beyond this package), or `.infrastructure` from outside this module —
this file and `dto.py` are the entire allowed surface today. This port
is the contract every future coding-aware module (Billing Engine,
Insurance Claims, DRG Coding, SNOMED CT Mapping, FHIR Condition
Resource, Medical Analytics) is expected to depend on to read a
clinical note's or patient's assigned ICD-10 codes — the same shape
`app.modules.differential_diagnosis.public.interfaces
.DifferentialDiagnosisQueryPort` already establishes for its own
one-to-many place under `ClinicalNote`. `is_editable` is what every one
of those future consumers is expected to check before writing to a
coding record.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.icd10_coding.public.dto import ICD10CodingSummaryDTO


class ICD10CodingQueryPort(ABC):
    @abstractmethod
    async def icd10_coding_exists(self, icd10_coding_id: UUID) -> bool: ...

    @abstractmethod
    async def is_editable(self, icd10_coding_id: UUID) -> bool: ...

    @abstractmethod
    async def get_icd10_coding_summary(
        self, icd10_coding_id: UUID
    ) -> ICD10CodingSummaryDTO | None: ...

    @abstractmethod
    async def get_primary_icd10_coding_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> ICD10CodingSummaryDTO | None: ...

    @abstractmethod
    async def list_icd10_codings_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> list[ICD10CodingSummaryDTO]: ...

    @abstractmethod
    async def list_icd10_codings_for_patient(
        self, patient_id: UUID
    ) -> list[ICD10CodingSummaryDTO]: ...
