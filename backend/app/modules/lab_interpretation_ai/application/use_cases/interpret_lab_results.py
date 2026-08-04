"""`InterpretLabResultsUseCase` — orchestrates the pipeline this task
specifies:

    (input already validated by `LabInterpretationInput.__post_init__`)
    -> `LabInterpreterPort.generate` (prompt selection, prompt rendering,
       provider selection, and the LLM call all happen inside this one
       port call — see `infrastructure/generation
       /lab_interpretation_generator.py`)
    -> `LabInterpretationParserPort.parse` (raw AI text -> structured
       `LabInterpretationResult`)
    -> `LabInterpretationValidatorPort.validate` (missing-reasoning/
       hallucinated-values)
    -> enrichment, entirely non-throwing, applied only after the AI's own
       output has already passed validation:
       - `CriticalValueDetectionService.reconcile_findings` (the
         critical-value safety net)
       - `LabTrendAnalysisService.analyze_all_trends`, merged into
         `supporting_evidence` (lab trend analysis)
       - `LabRecommendationService.derive_follow_up_for_critical_findings`,
         merged into `suggested_follow_up_tests` (lab recommendations)
       - `LabRecommendationService.deduplicate`, applied defensively to
         every list-shaped output field
       - `MedicalReasoningAIPort.score_confidence` (confidence scoring —
         see this module's genuine reuse of
         `app.modules.medical_reasoning_ai`, documented in full in
         `container.py`'s own module docstring)
    -> audit logging (success or failure)
    -> return `GeneratedLabInterpretation`

Only this module's **own** exceptions (raised by the parser/validator
steps) are caught and turned into an audit `log_failure` entry — errors
originating from AI Foundation, or from
`app.modules.medical_reasoning_ai`'s own facade, during `generator
.generate()`/`self._medical_reasoning.score_confidence()` propagate
unwrapped and unaudited-by-this-module, the same reasoning every prior
AI module's own use case documents for itself.
"""

from dataclasses import replace

from app.modules.lab_interpretation_ai.application.dto import GeneratedLabInterpretation
from app.modules.lab_interpretation_ai.application.ports import (
    LabInterpretationAuditLoggerPort,
    LabInterpretationParserPort,
    LabInterpretationValidatorPort,
    LabInterpreterPort,
)
from app.modules.lab_interpretation_ai.application.services.critical_value_detection_service import (  # noqa: E501
    CriticalValueDetectionService,
)
from app.modules.lab_interpretation_ai.application.services.lab_recommendation_service import (
    LabRecommendationService,
)
from app.modules.lab_interpretation_ai.application.services.lab_trend_analysis_service import (
    LabTrendAnalysisService,
)
from app.modules.lab_interpretation_ai.domain.exceptions import (
    HallucinatedLabValueError,
    InvalidLabInterpretationResponseFormatError,
    MissingLabReasoningError,
)
from app.modules.lab_interpretation_ai.domain.value_objects import (
    LabInterpretationInput,
    LabInterpretationResult,
)
from app.modules.medical_reasoning_ai.public.interfaces import MedicalReasoningAIPort
from app.shared.application.use_case import UseCase

_LOCAL_PIPELINE_ERRORS = (
    InvalidLabInterpretationResponseFormatError,
    MissingLabReasoningError,
    HallucinatedLabValueError,
)


class InterpretLabResultsUseCase(UseCase[LabInterpretationInput, GeneratedLabInterpretation]):
    def __init__(
        self,
        *,
        generator: LabInterpreterPort,
        parser: LabInterpretationParserPort,
        validator: LabInterpretationValidatorPort,
        critical_value_service: CriticalValueDetectionService,
        trend_service: LabTrendAnalysisService,
        recommendation_service: LabRecommendationService,
        medical_reasoning: MedicalReasoningAIPort,
        audit_logger: LabInterpretationAuditLoggerPort,
    ) -> None:
        self._generator = generator
        self._parser = parser
        self._validator = validator
        self._critical_value_service = critical_value_service
        self._trend_service = trend_service
        self._recommendation_service = recommendation_service
        self._medical_reasoning = medical_reasoning
        self._audit_logger = audit_logger

    async def execute(self, input_dto: LabInterpretationInput) -> GeneratedLabInterpretation:
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

        enriched_result = await self._enrich(result, input_dto)

        await self._audit_logger.log_generation(
            session, organization_id=input_dto.organization_id, patient_id=input_dto.patient_id
        )
        return GeneratedLabInterpretation(result=enriched_result, session=session)

    async def _enrich(
        self, result: LabInterpretationResult, input_dto: LabInterpretationInput
    ) -> LabInterpretationResult:
        reconciled_findings = self._critical_value_service.reconcile_findings(result.findings)

        trend_descriptions = self._trend_service.analyze_all_trends(input_dto.lab_values)
        merged_supporting_evidence = self._recommendation_service.deduplicate(
            result.supporting_evidence + trend_descriptions
        )

        derived_follow_ups = self._recommendation_service.derive_follow_up_for_critical_findings(
            reconciled_findings
        )
        merged_follow_ups = self._recommendation_service.deduplicate(
            result.suggested_follow_up_tests + derived_follow_ups
        )

        merged_monitoring = self._recommendation_service.deduplicate(
            result.monitoring_recommendations
        )
        merged_red_flags = self._recommendation_service.deduplicate(result.red_flag_warnings)
        merged_causes = self._recommendation_service.deduplicate(result.potential_causes)

        confidence_score = self._medical_reasoning.score_confidence(
            ai_reported=result.confidence_score,
            supporting_count=len(merged_supporting_evidence),
            contradicting_count=0,
            missing_information_count=0,
        )

        return replace(
            result,
            findings=reconciled_findings,
            supporting_evidence=merged_supporting_evidence,
            potential_causes=merged_causes,
            suggested_follow_up_tests=merged_follow_ups,
            monitoring_recommendations=merged_monitoring,
            red_flag_warnings=merged_red_flags,
            confidence_score=confidence_score,
        )
