"""`GenerateClinicalReasoningUseCase` — orchestrates the pipeline this
task specifies:

    (input already validated by `MedicalReasoningInput.__post_init__`)
    -> `MedicalReasoningPort.generate` (prompt selection, prompt
       rendering, provider selection, and the LLM call all happen inside
       this one port call — see `infrastructure/generation
       /medical_reasoning_generator.py`)
    -> `MedicalReasoningParserPort.parse` (raw AI text -> structured
       `MedicalReasoningResult`)
    -> `MedicalReasoningValidatorPort.validate` (empty/missing-reasoning/
       duplicate-evidence/invalid-confidence/hallucinated-placeholder/
       inconsistent-recommendations)
    -> enrichment, entirely non-throwing, applied only after the AI's own
       output has already passed validation:
       - `EvidenceAnalysisService.weight_evidence` (evidence weighting)
       - `EvidenceAnalysisService.assess_missing_information`, merged
         with whatever the AI itself already reported (missing-
         information analysis)
       - `EvidenceAnalysisService.prioritize_red_flags` (risk scoring +
         red flag prioritization)
       - `ConfidenceScoringService.score`, applied independently to each
         of the three confidence dimensions (confidence scoring)
       - `RecommendationReasoningService.deduplicate`, applied
         defensively to each recommendation list (already validated
         duplicate-free, but idempotent to run again)
    -> audit logging (success or failure)
    -> return `GeneratedMedicalReasoning`

Only this module's **own** exceptions (raised by the parser/validator
steps) are caught and turned into an audit `log_failure` entry — errors
originating from AI Foundation during `generator.generate()` propagate
unwrapped and unaudited-by-this-module, the same reasoning
`app.modules.differential_diagnosis_ai.application.use_cases
.generate_differential_diagnosis.GenerateDifferentialDiagnosisUseCase`
documents for itself.
"""

from dataclasses import replace

from app.modules.medical_reasoning_ai.application.dto import GeneratedMedicalReasoning
from app.modules.medical_reasoning_ai.application.ports import (
    MedicalReasoningAuditLoggerPort,
    MedicalReasoningParserPort,
    MedicalReasoningPort,
    MedicalReasoningValidatorPort,
)
from app.modules.medical_reasoning_ai.application.services.confidence_scoring_service import (
    ConfidenceScoringService,
)
from app.modules.medical_reasoning_ai.application.services.evidence_analysis_service import (
    EvidenceAnalysisService,
)
from app.modules.medical_reasoning_ai.application.services.recommendation_reasoning_service import (
    RecommendationReasoningService,
)
from app.modules.medical_reasoning_ai.domain.exceptions import (
    DuplicateEvidenceError,
    EmptyReasoningResponseError,
    HallucinatedReasoningPlaceholderError,
    InconsistentRecommendationsError,
    InvalidConfidenceValueError,
    InvalidMedicalReasoningResponseFormatError,
    MissingReasoningError,
)
from app.modules.medical_reasoning_ai.domain.value_objects import (
    MedicalReasoningInput,
    MedicalReasoningResult,
)
from app.shared.application.use_case import UseCase

_LOCAL_PIPELINE_ERRORS = (
    InvalidMedicalReasoningResponseFormatError,
    EmptyReasoningResponseError,
    MissingReasoningError,
    DuplicateEvidenceError,
    InvalidConfidenceValueError,
    HallucinatedReasoningPlaceholderError,
    InconsistentRecommendationsError,
)


class GenerateClinicalReasoningUseCase(UseCase[MedicalReasoningInput, GeneratedMedicalReasoning]):
    def __init__(
        self,
        *,
        generator: MedicalReasoningPort,
        parser: MedicalReasoningParserPort,
        validator: MedicalReasoningValidatorPort,
        evidence_service: EvidenceAnalysisService,
        confidence_service: ConfidenceScoringService,
        recommendation_service: RecommendationReasoningService,
        audit_logger: MedicalReasoningAuditLoggerPort,
    ) -> None:
        self._generator = generator
        self._parser = parser
        self._validator = validator
        self._evidence_service = evidence_service
        self._confidence_service = confidence_service
        self._recommendation_service = recommendation_service
        self._audit_logger = audit_logger

    async def execute(self, input_dto: MedicalReasoningInput) -> GeneratedMedicalReasoning:
        raw_text, session = await self._generator.generate(input_dto)

        try:
            result = self._parser.parse(raw_text, output_format=input_dto.output_format)
            self._validator.validate(result)
        except _LOCAL_PIPELINE_ERRORS as exc:
            await self._audit_logger.log_failure(
                generation_id=session.generation_id,
                organization_id=input_dto.organization_id,
                patient_id=input_dto.patient_id,
                stage="parse_or_validate",
                error_code=type(exc).__name__,
                message=str(exc),
            )
            raise

        enriched_result = self._enrich(result, input_dto)

        await self._audit_logger.log_generation(
            session, organization_id=input_dto.organization_id, patient_id=input_dto.patient_id
        )
        return GeneratedMedicalReasoning(result=enriched_result, session=session)

    def _enrich(
        self, result: MedicalReasoningResult, input_dto: MedicalReasoningInput
    ) -> MedicalReasoningResult:
        weighted_evidence = self._evidence_service.weight_evidence(result.evidence)

        inferred_missing = self._evidence_service.assess_missing_information(input_dto)
        merged_missing = self._recommendation_service.deduplicate(
            result.missing_information + inferred_missing
        )

        prioritized_flags = self._evidence_service.prioritize_red_flags(
            risk_factors=result.risk_factors, red_flags=result.red_flags
        )

        supporting_count = len(
            [item for item in weighted_evidence if item.polarity.value == "supporting"]
        )
        contradicting_count = len(weighted_evidence) - supporting_count
        missing_count = len(merged_missing)

        clinical_confidence = self._confidence_service.score(
            ai_reported=result.clinical_confidence,
            supporting_count=supporting_count,
            contradicting_count=contradicting_count,
            missing_information_count=missing_count,
        )
        diagnostic_confidence = self._confidence_service.score(
            ai_reported=result.diagnostic_confidence,
            supporting_count=supporting_count,
            contradicting_count=contradicting_count,
            missing_information_count=missing_count,
        )
        therapeutic_confidence = self._confidence_service.score(
            ai_reported=result.therapeutic_confidence,
            supporting_count=supporting_count,
            contradicting_count=contradicting_count,
            missing_information_count=missing_count,
        )

        return replace(
            result,
            evidence=weighted_evidence,
            missing_information=merged_missing,
            red_flags=prioritized_flags,
            clinical_confidence=clinical_confidence,
            diagnostic_confidence=diagnostic_confidence,
            therapeutic_confidence=therapeutic_confidence,
            suggested_next_questions=self._recommendation_service.deduplicate(
                result.suggested_next_questions
            ),
            suggested_investigations=self._recommendation_service.deduplicate(
                result.suggested_investigations
            ),
            suggested_monitoring=self._recommendation_service.deduplicate(
                result.suggested_monitoring
            ),
        )
