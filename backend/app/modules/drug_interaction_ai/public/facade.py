"""`DrugInteractionAIFacade` — the one concrete implementation of
`DrugInteractionAIPort`. Constructed by
`app.modules.drug_interaction_ai.container.get_drug_interaction_ai_facade`.

`render_result` delegates directly to `DrugSafetyReportRenderer` (not a
use case) — this task names exactly one use case,
`AnalyzeMedicationSafetyUseCase`, the same "no use case wraps rendering"
choice every prior AI module's own facade makes for its own renderer.
"""

from collections.abc import AsyncIterator

from app.modules.drug_interaction_ai.application.ports import DrugSafetyAnalysisGeneratorPort
from app.modules.drug_interaction_ai.application.services.drug_safety_report_renderer import (
    DrugSafetyReportRenderer,
)
from app.modules.drug_interaction_ai.application.use_cases.analyze_medication_safety import (
    AnalyzeMedicationSafetyUseCase,
)
from app.modules.drug_interaction_ai.public.dto import (
    DrugInteractionAnalysisInput,
    DrugInteractionAnalysisResult,
    DrugInteractionOutputFormat,
    DrugInteractionStreamChunk,
    GeneratedDrugInteractionAnalysis,
)
from app.modules.drug_interaction_ai.public.interfaces import DrugInteractionAIPort


class DrugInteractionAIFacade(DrugInteractionAIPort):
    def __init__(
        self,
        *,
        analyze_use_case: AnalyzeMedicationSafetyUseCase,
        renderer: DrugSafetyReportRenderer,
        generator: DrugSafetyAnalysisGeneratorPort,
    ) -> None:
        self._analyze_use_case = analyze_use_case
        self._renderer = renderer
        self._generator = generator

    async def analyze_medication_safety(
        self, input_dto: DrugInteractionAnalysisInput
    ) -> GeneratedDrugInteractionAnalysis:
        return await self._analyze_use_case.execute(input_dto)

    def stream_analyze_medication_safety(
        self, input_dto: DrugInteractionAnalysisInput
    ) -> AsyncIterator[DrugInteractionStreamChunk]:
        return self._generator.stream_generate(input_dto)

    async def render_result(
        self, result: DrugInteractionAnalysisResult, *, target_format: DrugInteractionOutputFormat
    ) -> str:
        return self._renderer.render(result, target_format)
