"""`RiskStratificationAIFacade` — the one concrete implementation of
`RiskStratificationAIPort`. Constructed by
`app.modules.risk_stratification_ai.container.get_risk_stratification_ai_facade`.

`render_result` delegates directly to `RiskReportRenderer` (not a use
case) — this task names exactly one use case,
`AnalyzePatientRiskUseCase`, the same "no use case wraps rendering"
choice every prior AI module's own facade makes for its own renderer.
"""

from collections.abc import AsyncIterator

from app.modules.risk_stratification_ai.application.ports import (
    RiskStratificationAnalysisGeneratorPort,
)
from app.modules.risk_stratification_ai.application.services.risk_report_renderer import (
    RiskReportRenderer,
)
from app.modules.risk_stratification_ai.application.use_cases.analyze_patient_risk import (
    AnalyzePatientRiskUseCase,
)
from app.modules.risk_stratification_ai.public.dto import (
    GeneratedRiskStratification,
    RiskStratificationInput,
    RiskStratificationOutputFormat,
    RiskStratificationResult,
    RiskStratificationStreamChunk,
)
from app.modules.risk_stratification_ai.public.interfaces import RiskStratificationAIPort


class RiskStratificationAIFacade(RiskStratificationAIPort):
    def __init__(
        self,
        *,
        analyze_use_case: AnalyzePatientRiskUseCase,
        renderer: RiskReportRenderer,
        generator: RiskStratificationAnalysisGeneratorPort,
    ) -> None:
        self._analyze_use_case = analyze_use_case
        self._renderer = renderer
        self._generator = generator

    async def analyze_patient_risk(
        self, input_dto: RiskStratificationInput
    ) -> GeneratedRiskStratification:
        return await self._analyze_use_case.execute(input_dto)

    def stream_analyze_patient_risk(
        self, input_dto: RiskStratificationInput
    ) -> AsyncIterator[RiskStratificationStreamChunk]:
        return self._generator.stream_generate(input_dto)

    async def render_result(
        self,
        result: RiskStratificationResult,
        *,
        target_format: RiskStratificationOutputFormat,
    ) -> str:
        return self._renderer.render(result, target_format)
