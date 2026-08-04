"""The AI Medical Reasoning Engine's public port — the only contract
another module may depend on
(`docs/backend-architecture/03_module_architecture.md`,
`10_module_communication.md`).

Never import from `app.modules.medical_reasoning_ai.domain`,
`.application` (beyond this package's own re-exports in `public/dto.py`),
or `.infrastructure` from outside this module. This task's own GOAL
section frames this module as "the reusable reasoning layer used by" AI
Clinical Copilot, AI Clinical Note AI, AI SOAP Note AI, AI ICD-10 AI, AI
Prescription AI, AI Differential Diagnosis AI, and future AI modules —
this port is exactly the seam a future such caller depends on. See
`container.py`'s own scope note for why none of those six *existing*
modules are retrofitted to call through it as part of *this* task.

Exposes more than the one generation pipeline deliberately: `weight_evidence`
and `score_confidence` surface `EvidenceAnalysisService`/
`ConfidenceScoringService`'s own capabilities directly, so a future
caller that already has an assembled evidence list or confidence inputs
of its own can reuse this module's reasoning logic without going through
a full AI generation — the literal fulfillment of this task's own
"centralize clinical reasoning so no AI module duplicates reasoning
logic" charter.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.modules.medical_reasoning_ai.public.dto import (
    EvidenceItem,
    GeneratedMedicalReasoning,
    MedicalReasoningInput,
    MedicalReasoningOutputFormat,
    MedicalReasoningResult,
    MedicalReasoningStreamChunk,
)


class MedicalReasoningAIPort(ABC):
    @abstractmethod
    async def generate_reasoning(
        self, evidence: MedicalReasoningInput
    ) -> GeneratedMedicalReasoning: ...

    @abstractmethod
    def stream_generate_reasoning(
        self, evidence: MedicalReasoningInput
    ) -> AsyncIterator[MedicalReasoningStreamChunk]: ...

    @abstractmethod
    async def render_result(
        self, result: MedicalReasoningResult, *, target_format: MedicalReasoningOutputFormat
    ) -> str: ...

    @abstractmethod
    def weight_evidence(self, items: tuple[EvidenceItem, ...]) -> tuple[EvidenceItem, ...]: ...

    @abstractmethod
    def score_confidence(
        self,
        *,
        ai_reported: float | None,
        supporting_count: int,
        contradicting_count: int,
        missing_information_count: int,
    ) -> float: ...
