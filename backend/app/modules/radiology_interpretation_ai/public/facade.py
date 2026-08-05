"""`RadiologyInterpretationAIFacade` — the one concrete implementation of
`RadiologyInterpretationAIPort`. Constructed by
`app.modules.radiology_interpretation_ai.container
.get_radiology_interpretation_ai_facade`.

`render_result` delegates directly to `RadiologySummaryService` (not a
use case) — this task names exactly one use case,
`InterpretRadiologyReportUseCase`, the same "no use case wraps
rendering" choice every prior AI module's own facade makes for its own
renderer. `extract_candidate_findings` delegates directly to
`FindingExtractionService` — see `public/interfaces.py
::RadiologyInterpretationAIPort`'s own docstring for why that capability
is deliberately exposed standalone.
"""

from collections.abc import AsyncIterator

from app.modules.radiology_interpretation_ai.application.ports import RadiologyInterpreterPort
from app.modules.radiology_interpretation_ai.application.services.finding_extraction_service import (  # noqa: E501
    FindingExtractionService,
)
from app.modules.radiology_interpretation_ai.application.services.radiology_summary_service import (  # noqa: E501
    RadiologySummaryService,
)
from app.modules.radiology_interpretation_ai.application.use_cases.interpret_radiology_report import (  # noqa: E501
    InterpretRadiologyReportUseCase,
)
from app.modules.radiology_interpretation_ai.public.dto import (
    GeneratedRadiologyInterpretation,
    RadiologyFinding,
    RadiologyInterpretationInput,
    RadiologyInterpretationResult,
    RadiologyInterpretationStreamChunk,
    RadiologyOutputFormat,
)
from app.modules.radiology_interpretation_ai.public.interfaces import (
    RadiologyInterpretationAIPort,
)


class RadiologyInterpretationAIFacade(RadiologyInterpretationAIPort):
    def __init__(
        self,
        *,
        generate_use_case: InterpretRadiologyReportUseCase,
        finding_extraction_service: FindingExtractionService,
        summary_service: RadiologySummaryService,
        generator: RadiologyInterpreterPort,
    ) -> None:
        self._generate_use_case = generate_use_case
        self._finding_extraction_service = finding_extraction_service
        self._summary_service = summary_service
        self._generator = generator

    async def generate_interpretation(
        self, input_dto: RadiologyInterpretationInput
    ) -> GeneratedRadiologyInterpretation:
        return await self._generate_use_case.execute(input_dto)

    def stream_generate_interpretation(
        self, input_dto: RadiologyInterpretationInput
    ) -> AsyncIterator[RadiologyInterpretationStreamChunk]:
        return self._generator.stream_generate(input_dto)

    async def render_result(
        self, result: RadiologyInterpretationResult, *, target_format: RadiologyOutputFormat
    ) -> str:
        return self._summary_service.render(result, target_format)

    def extract_candidate_findings(self, report_text: str) -> tuple[RadiologyFinding, ...]:
        return self._finding_extraction_service.extract(report_text)
