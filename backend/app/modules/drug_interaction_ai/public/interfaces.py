"""The AI Drug Interaction & Medication Safety module's public port —
the only contract another module may depend on
(`docs/backend-architecture/03_module_architecture.md`,
`10_module_communication.md`).

Never import from `app.modules.drug_interaction_ai.domain`,
`.application` (beyond this package's own re-exports in `public/dto.py`),
or `.infrastructure` from outside this module.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.modules.drug_interaction_ai.public.dto import (
    DrugInteractionAnalysisInput,
    DrugInteractionAnalysisResult,
    DrugInteractionOutputFormat,
    DrugInteractionStreamChunk,
    GeneratedDrugInteractionAnalysis,
)


class DrugInteractionAIPort(ABC):
    @abstractmethod
    async def analyze_medication_safety(
        self, input_dto: DrugInteractionAnalysisInput
    ) -> GeneratedDrugInteractionAnalysis: ...

    @abstractmethod
    def stream_analyze_medication_safety(
        self, input_dto: DrugInteractionAnalysisInput
    ) -> AsyncIterator[DrugInteractionStreamChunk]: ...

    @abstractmethod
    async def render_result(
        self, result: DrugInteractionAnalysisResult, *, target_format: DrugInteractionOutputFormat
    ) -> str: ...
