"""`PathologyInterpretationAIFacade` — the one concrete implementation of
`PathologyInterpretationAIPort`. Constructed by
`app.modules.pathology_interpretation_ai.container
.get_pathology_interpretation_ai_facade`.

`render_result` delegates directly to `PathologySummaryService` (not a
use case) — this task names exactly one use case,
`InterpretPathologyReportUseCase`, the same "no use case wraps
rendering" choice every prior AI module's own facade makes for its own
renderer. `extract_candidate_findings` delegates directly to
`FindingExtractionService` — see `public/interfaces.py
::PathologyInterpretationAIPort`'s own docstring for why that capability
is deliberately exposed standalone.
"""

from collections.abc import AsyncIterator

from app.modules.pathology_interpretation_ai.application.ports import PathologyInterpreterPort
from app.modules.pathology_interpretation_ai.application.services.finding_extraction_service import (  # noqa: E501
    FindingExtractionService,
)
from app.modules.pathology_interpretation_ai.application.services.pathology_summary_service import (  # noqa: E501
    PathologySummaryService,
)
from app.modules.pathology_interpretation_ai.application.use_cases.interpret_pathology_report import (  # noqa: E501
    InterpretPathologyReportUseCase,
)
from app.modules.pathology_interpretation_ai.public.dto import (
    GeneratedPathologyInterpretation,
    PathologyFinding,
    PathologyInterpretationInput,
    PathologyInterpretationResult,
    PathologyInterpretationStreamChunk,
    PathologyOutputFormat,
)
from app.modules.pathology_interpretation_ai.public.interfaces import (
    PathologyInterpretationAIPort,
)


class PathologyInterpretationAIFacade(PathologyInterpretationAIPort):
    def __init__(
        self,
        *,
        generate_use_case: InterpretPathologyReportUseCase,
        finding_extraction_service: FindingExtractionService,
        summary_service: PathologySummaryService,
        generator: PathologyInterpreterPort,
    ) -> None:
        self._generate_use_case = generate_use_case
        self._finding_extraction_service = finding_extraction_service
        self._summary_service = summary_service
        self._generator = generator

    async def generate_interpretation(
        self, input_dto: PathologyInterpretationInput
    ) -> GeneratedPathologyInterpretation:
        return await self._generate_use_case.execute(input_dto)

    def stream_generate_interpretation(
        self, input_dto: PathologyInterpretationInput
    ) -> AsyncIterator[PathologyInterpretationStreamChunk]:
        return self._generator.stream_generate(input_dto)

    async def render_result(
        self, result: PathologyInterpretationResult, *, target_format: PathologyOutputFormat
    ) -> str:
        return self._summary_service.render(result, target_format)

    def extract_candidate_findings(self, report_text: str) -> tuple[PathologyFinding, ...]:
        return self._finding_extraction_service.extract(report_text)
