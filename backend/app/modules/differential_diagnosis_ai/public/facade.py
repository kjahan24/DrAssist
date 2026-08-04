"""`DifferentialDiagnosisAIFacade` — the one concrete implementation of
`DifferentialDiagnosisAIPort`. Constructed by
`app.modules.differential_diagnosis_ai.container
.get_differential_diagnosis_ai_facade`.

`render_result` delegates directly to `DifferentialDiagnosisRenderer`
(not a use case) — see that service's own module docstring for why: this
task names exactly three use cases, none of them a rendering one.
"""

from collections.abc import AsyncIterator

from app.modules.differential_diagnosis_ai.application.ports import (
    DifferentialDiagnosisGeneratorPort,
)
from app.modules.differential_diagnosis_ai.application.services.differential_diagnosis_renderer import (  # noqa: E501
    DifferentialDiagnosisRenderer,
)
from app.modules.differential_diagnosis_ai.application.use_cases.generate_differential_diagnosis import (  # noqa: E501
    GenerateDifferentialDiagnosisUseCase,
)
from app.modules.differential_diagnosis_ai.application.use_cases.rank_differential_diagnosis import (  # noqa: E501
    RankDifferentialDiagnosisUseCase,
)
from app.modules.differential_diagnosis_ai.application.use_cases.validate_clinical_evidence import (  # noqa: E501
    ValidateClinicalEvidenceUseCase,
)
from app.modules.differential_diagnosis_ai.public.dto import (
    ClinicalEvidenceValidationResultDTO,
    DifferentialDiagnosisInput,
    DifferentialDiagnosisResult,
    DifferentialDiagnosisStreamChunk,
    DifferentialOutputFormat,
    GeneratedDifferentialDiagnosis,
)
from app.modules.differential_diagnosis_ai.public.interfaces import DifferentialDiagnosisAIPort


class DifferentialDiagnosisAIFacade(DifferentialDiagnosisAIPort):
    def __init__(
        self,
        *,
        generate_use_case: GenerateDifferentialDiagnosisUseCase,
        rank_use_case: RankDifferentialDiagnosisUseCase,
        validate_use_case: ValidateClinicalEvidenceUseCase,
        renderer: DifferentialDiagnosisRenderer,
        generator: DifferentialDiagnosisGeneratorPort,
    ) -> None:
        self._generate_use_case = generate_use_case
        self._rank_use_case = rank_use_case
        self._validate_use_case = validate_use_case
        self._renderer = renderer
        self._generator = generator

    async def generate_differential_diagnosis(
        self, evidence: DifferentialDiagnosisInput
    ) -> GeneratedDifferentialDiagnosis:
        return await self._generate_use_case.execute(evidence)

    def stream_generate_differential_diagnosis(
        self, evidence: DifferentialDiagnosisInput
    ) -> AsyncIterator[DifferentialDiagnosisStreamChunk]:
        return self._generator.stream_generate(evidence)

    async def rank_result(self, result: DifferentialDiagnosisResult) -> DifferentialDiagnosisResult:
        return await self._rank_use_case.execute(result)

    async def render_result(
        self, result: DifferentialDiagnosisResult, *, target_format: DifferentialOutputFormat
    ) -> str:
        return self._renderer.render(result, target_format)

    async def validate_evidence(
        self, evidence: DifferentialDiagnosisInput
    ) -> ClinicalEvidenceValidationResultDTO:
        return await self._validate_use_case.execute(evidence)
