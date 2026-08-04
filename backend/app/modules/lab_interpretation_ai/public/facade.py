"""`LabInterpretationAIFacade` — the one concrete implementation of
`LabInterpretationAIPort`. Constructed by `app.modules.lab_interpretation_ai
.container.get_lab_interpretation_ai_facade`.

`render_result` delegates directly to `LabInterpretationRenderer` (not a
use case) — this task names exactly one use case,
`InterpretLabResultsUseCase`, the same "no use case wraps rendering"
choice every prior AI module's own facade makes for its own renderer.
"""

from collections.abc import AsyncIterator

from app.modules.lab_interpretation_ai.application.ports import LabInterpreterPort
from app.modules.lab_interpretation_ai.application.services.lab_interpretation_renderer import (
    LabInterpretationRenderer,
)
from app.modules.lab_interpretation_ai.application.use_cases.interpret_lab_results import (
    InterpretLabResultsUseCase,
)
from app.modules.lab_interpretation_ai.public.dto import (
    GeneratedLabInterpretation,
    LabInterpretationInput,
    LabInterpretationOutputFormat,
    LabInterpretationResult,
    LabInterpretationStreamChunk,
)
from app.modules.lab_interpretation_ai.public.interfaces import LabInterpretationAIPort


class LabInterpretationAIFacade(LabInterpretationAIPort):
    def __init__(
        self,
        *,
        generate_use_case: InterpretLabResultsUseCase,
        renderer: LabInterpretationRenderer,
        generator: LabInterpreterPort,
    ) -> None:
        self._generate_use_case = generate_use_case
        self._renderer = renderer
        self._generator = generator

    async def generate_interpretation(
        self, input_dto: LabInterpretationInput
    ) -> GeneratedLabInterpretation:
        return await self._generate_use_case.execute(input_dto)

    def stream_generate_interpretation(
        self, input_dto: LabInterpretationInput
    ) -> AsyncIterator[LabInterpretationStreamChunk]:
        return self._generator.stream_generate(input_dto)

    async def render_result(
        self, result: LabInterpretationResult, *, target_format: LabInterpretationOutputFormat
    ) -> str:
        return self._renderer.render(result, target_format)
