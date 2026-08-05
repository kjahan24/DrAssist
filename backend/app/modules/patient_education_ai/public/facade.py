"""`PatientEducationAIFacade` — the one concrete implementation of
`PatientEducationAIPort`. Constructed by
`app.modules.patient_education_ai.container.get_patient_education_ai_facade`.

`render_result` delegates directly to `PatientEducationReportRenderer`
(not a use case) — this task names exactly one use case,
`GeneratePatientEducationUseCase`, the same "no use case wraps
rendering" choice every prior AI module's own facade makes for its own
renderer.
"""

from collections.abc import AsyncIterator

from app.modules.patient_education_ai.application.ports import (
    PatientEducationAnalysisGeneratorPort,
)
from app.modules.patient_education_ai.application.services.patient_education_report_renderer import (  # noqa: E501
    PatientEducationReportRenderer,
)
from app.modules.patient_education_ai.application.use_cases.generate_patient_education import (
    GeneratePatientEducationUseCase,
)
from app.modules.patient_education_ai.public.dto import (
    GeneratedPatientEducation,
    PatientEducationInput,
    PatientEducationOutputFormat,
    PatientEducationResult,
    PatientEducationStreamChunk,
)
from app.modules.patient_education_ai.public.interfaces import PatientEducationAIPort


class PatientEducationAIFacade(PatientEducationAIPort):
    def __init__(
        self,
        *,
        generate_use_case: GeneratePatientEducationUseCase,
        renderer: PatientEducationReportRenderer,
        generator: PatientEducationAnalysisGeneratorPort,
    ) -> None:
        self._generate_use_case = generate_use_case
        self._renderer = renderer
        self._generator = generator

    async def generate_patient_education(
        self, input_dto: PatientEducationInput
    ) -> GeneratedPatientEducation:
        return await self._generate_use_case.execute(input_dto)

    def stream_generate_patient_education(
        self, input_dto: PatientEducationInput
    ) -> AsyncIterator[PatientEducationStreamChunk]:
        return self._generator.stream_generate(input_dto)

    async def render_result(
        self,
        result: PatientEducationResult,
        *,
        target_format: PatientEducationOutputFormat,
    ) -> str:
        return self._renderer.render(result, target_format)
