"""The AI Radiology Interpretation module's public port — the only
contract another module may depend on
(`docs/backend-architecture/03_module_architecture.md`,
`10_module_communication.md`).

Never import from `app.modules.radiology_interpretation_ai.domain`,
`.application` (beyond this package's own re-exports in `public/dto.py`),
or `.infrastructure` from outside this module.

Exposes more than the one generation pipeline deliberately:
`extract_candidate_findings` surfaces `FindingExtractionService`'s own
capability directly, so a future caller that already has raw report text
of its own can reuse this module's deterministic keyword extraction
without going through a full AI generation — the same "expose a
standalone, primitive-typed capability beyond the main pipeline" choice
`app.modules.medical_reasoning_ai.public.interfaces.MedicalReasoningAIPort
.weight_evidence`/`.score_confidence` make for their own module.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.modules.radiology_interpretation_ai.public.dto import (
    GeneratedRadiologyInterpretation,
    RadiologyFinding,
    RadiologyInterpretationInput,
    RadiologyInterpretationResult,
    RadiologyInterpretationStreamChunk,
    RadiologyOutputFormat,
)


class RadiologyInterpretationAIPort(ABC):
    @abstractmethod
    async def generate_interpretation(
        self, input_dto: RadiologyInterpretationInput
    ) -> GeneratedRadiologyInterpretation: ...

    @abstractmethod
    def stream_generate_interpretation(
        self, input_dto: RadiologyInterpretationInput
    ) -> AsyncIterator[RadiologyInterpretationStreamChunk]: ...

    @abstractmethod
    async def render_result(
        self, result: RadiologyInterpretationResult, *, target_format: RadiologyOutputFormat
    ) -> str: ...

    @abstractmethod
    def extract_candidate_findings(self, report_text: str) -> tuple[RadiologyFinding, ...]: ...
