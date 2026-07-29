"""The Clinical Reasoning module's public port — the only contract
another module may depend on. See
`docs/backend-architecture/03_module_architecture.md` and
`10_module_communication.md`.

Never import from `app.modules.clinical_reasoning.domain`, `.application`
(beyond this package), or `.infrastructure` from outside this module —
this file and `dto.py` are the entire allowed surface today. This port is
the contract every future reasoning-aware module (Differential Diagnosis,
ICD-10 Coding, AI Copilot, LLM Providers, Prompt Management, Human Review
Workflow, Clinical Timeline) is expected to depend on to read a patient's
recorded clinical reasoning — the same shape
`app.modules.lab_orders.public.interfaces.LabOrderQueryPort` already
establishes for its own one-to-many place under `ClinicalNote`.
`is_editable` is what every one of those future consumers is expected to
check before writing to a reasoning record.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.clinical_reasoning.public.dto import ClinicalReasoningSummaryDTO


class ClinicalReasoningQueryPort(ABC):
    @abstractmethod
    async def clinical_reasoning_exists(self, clinical_reasoning_id: UUID) -> bool: ...

    @abstractmethod
    async def is_editable(self, clinical_reasoning_id: UUID) -> bool: ...

    @abstractmethod
    async def get_clinical_reasoning_summary(
        self, clinical_reasoning_id: UUID
    ) -> ClinicalReasoningSummaryDTO | None: ...

    @abstractmethod
    async def list_clinical_reasoning_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> list[ClinicalReasoningSummaryDTO]: ...

    @abstractmethod
    async def list_clinical_reasoning_for_patient(
        self, patient_id: UUID
    ) -> list[ClinicalReasoningSummaryDTO]: ...
