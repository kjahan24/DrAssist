"""`MedicalReasoningAIFacade` — the one concrete implementation of
`MedicalReasoningAIPort`. Constructed by `app.modules.medical_reasoning_ai
.container.get_medical_reasoning_ai_facade`.

`render_result` delegates directly to `ClinicalSummaryService` (not a
use case) — see that service's own module docstring for why: this task
names exactly one use case, `GenerateClinicalReasoningUseCase`.
`weight_evidence`/`score_confidence` delegate directly to
`EvidenceAnalysisService`/`ConfidenceScoringService` — see
`public/interfaces.py::MedicalReasoningAIPort`'s own docstring for why
those two capabilities are deliberately exposed standalone.
"""

from collections.abc import AsyncIterator

from app.modules.medical_reasoning_ai.application.ports import MedicalReasoningPort
from app.modules.medical_reasoning_ai.application.services.clinical_summary_service import (
    ClinicalSummaryService,
)
from app.modules.medical_reasoning_ai.application.services.confidence_scoring_service import (
    ConfidenceScoringService,
)
from app.modules.medical_reasoning_ai.application.services.evidence_analysis_service import (
    EvidenceAnalysisService,
)
from app.modules.medical_reasoning_ai.application.use_cases.generate_clinical_reasoning import (
    GenerateClinicalReasoningUseCase,
)
from app.modules.medical_reasoning_ai.public.dto import (
    EvidenceItem,
    GeneratedMedicalReasoning,
    MedicalReasoningInput,
    MedicalReasoningOutputFormat,
    MedicalReasoningResult,
    MedicalReasoningStreamChunk,
)
from app.modules.medical_reasoning_ai.public.interfaces import MedicalReasoningAIPort


class MedicalReasoningAIFacade(MedicalReasoningAIPort):
    def __init__(
        self,
        *,
        generate_use_case: GenerateClinicalReasoningUseCase,
        evidence_service: EvidenceAnalysisService,
        confidence_service: ConfidenceScoringService,
        summary_service: ClinicalSummaryService,
        generator: MedicalReasoningPort,
    ) -> None:
        self._generate_use_case = generate_use_case
        self._evidence_service = evidence_service
        self._confidence_service = confidence_service
        self._summary_service = summary_service
        self._generator = generator

    async def generate_reasoning(
        self, evidence: MedicalReasoningInput
    ) -> GeneratedMedicalReasoning:
        return await self._generate_use_case.execute(evidence)

    def stream_generate_reasoning(
        self, evidence: MedicalReasoningInput
    ) -> AsyncIterator[MedicalReasoningStreamChunk]:
        return self._generator.stream_generate(evidence)

    async def render_result(
        self, result: MedicalReasoningResult, *, target_format: MedicalReasoningOutputFormat
    ) -> str:
        return self._summary_service.render(result, target_format)

    def weight_evidence(self, items: tuple[EvidenceItem, ...]) -> tuple[EvidenceItem, ...]:
        return self._evidence_service.weight_evidence(items)

    def score_confidence(
        self,
        *,
        ai_reported: float | None,
        supporting_count: int,
        contradicting_count: int,
        missing_information_count: int,
    ) -> float:
        return self._confidence_service.score(
            ai_reported=ai_reported,
            supporting_count=supporting_count,
            contradicting_count=contradicting_count,
            missing_information_count=missing_information_count,
        )
