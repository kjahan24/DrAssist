"""The AI Pathology Interpretation module's public port — the only
contract another module may depend on
(`docs/backend-architecture/03_module_architecture.md`,
`10_module_communication.md`).

Never import from `app.modules.pathology_interpretation_ai.domain`,
`.application` (beyond this package's own re-exports in `public/dto.py`),
or `.infrastructure` from outside this module.

Exposes more than the one generation pipeline deliberately:
`extract_candidate_findings` surfaces `FindingExtractionService`'s own
capability directly, so a future caller that already has raw report text
of its own can reuse this module's deterministic keyword extraction
without going through a full AI generation — the same "expose a
standalone, primitive-typed capability beyond the main pipeline" choice
`app.modules.radiology_interpretation_ai.public.interfaces
.RadiologyInterpretationAIPort.extract_candidate_findings` makes for its
own module.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.modules.pathology_interpretation_ai.public.dto import (
    GeneratedPathologyInterpretation,
    PathologyFinding,
    PathologyInterpretationInput,
    PathologyInterpretationResult,
    PathologyInterpretationStreamChunk,
    PathologyOutputFormat,
)


class PathologyInterpretationAIPort(ABC):
    @abstractmethod
    async def generate_interpretation(
        self, input_dto: PathologyInterpretationInput
    ) -> GeneratedPathologyInterpretation: ...

    @abstractmethod
    def stream_generate_interpretation(
        self, input_dto: PathologyInterpretationInput
    ) -> AsyncIterator[PathologyInterpretationStreamChunk]: ...

    @abstractmethod
    async def render_result(
        self, result: PathologyInterpretationResult, *, target_format: PathologyOutputFormat
    ) -> str: ...

    @abstractmethod
    def extract_candidate_findings(self, report_text: str) -> tuple[PathologyFinding, ...]: ...
