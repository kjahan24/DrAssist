"""The AI Lab Interpretation module's public port — the only contract
another module may depend on
(`docs/backend-architecture/03_module_architecture.md`,
`10_module_communication.md`).

Never import from `app.modules.lab_interpretation_ai.domain`,
`.application` (beyond this package's own re-exports in `public/dto.py`),
or `.infrastructure` from outside this module.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.modules.lab_interpretation_ai.public.dto import (
    GeneratedLabInterpretation,
    LabInterpretationInput,
    LabInterpretationOutputFormat,
    LabInterpretationResult,
    LabInterpretationStreamChunk,
)


class LabInterpretationAIPort(ABC):
    @abstractmethod
    async def generate_interpretation(
        self, input_dto: LabInterpretationInput
    ) -> GeneratedLabInterpretation: ...

    @abstractmethod
    def stream_generate_interpretation(
        self, input_dto: LabInterpretationInput
    ) -> AsyncIterator[LabInterpretationStreamChunk]: ...

    @abstractmethod
    async def render_result(
        self, result: LabInterpretationResult, *, target_format: LabInterpretationOutputFormat
    ) -> str: ...
