"""The AI Clinical Copilot module's public port — the only contract
another module may depend on
(`docs/backend-architecture/03_module_architecture.md`,
`10_module_communication.md`).

Never import from `app.modules.ai_copilot.domain`, `.application` (beyond
this package's own re-exports in `public/dto.py`), or `.infrastructure`
from outside this module. A future clinical-feature module (SOAP AI, ICD
AI, Prescription AI, Differential Diagnosis, ...) calls
`ClinicalCopilotPort.execute` with its own `request_type` and pre-
registered prompt templates — this port has no knowledge of what any
`request_type` actually means (per this task's own "orchestrates AI
requests... does not generate SOAP/ICD/prescriptions/diagnoses" scope).
"""

from abc import ABC, abstractmethod

from app.modules.ai_copilot.public.dto import AIRequest, AIResponse


class ClinicalCopilotPort(ABC):
    @abstractmethod
    async def execute(self, request: AIRequest) -> AIResponse: ...
