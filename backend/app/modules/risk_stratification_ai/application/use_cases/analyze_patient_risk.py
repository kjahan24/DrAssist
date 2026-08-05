"""`AnalyzePatientRiskUseCase` — orchestrates the pipeline this task
specifies:

    (input already validated by
     `RiskStratificationInput.__post_init__`)
    -> `RiskStratificationAnalysisGeneratorPort.generate` (prompt
       selection, prompt rendering, provider selection, and the LLM call
       all happen inside this one port call — see `infrastructure
       /generation/risk_stratification_generator.py`)
    -> `RiskStratificationAnalysisParserPort.parse` (raw AI text ->
       structured `RiskStratificationResult`)
    -> `RiskStratificationAnalysisValidatorPort.validate` (invalid
       scores/hallucinated risk factors/invalid confidence)
    -> enrichment, entirely non-throwing, applied only after the AI's own
       output has already passed validation:
       - `RiskScoringService.compute_standardized_scores` (real NEWS2/
         MEWS/qSOFA/SOFA-simplified, computed deterministically from
         `vital_signs`/`lab_values`)
       - `ClinicalRiskAssessmentService.assess_qualitative_risks` (the
         ten non-standardized categories' own curated risk-factor
         lookups)
       - `RiskExplanationService.merge_risk_scores` (the AI's own
         `risk_scores` reconciled against both deterministic sources
         above, one `RiskScore` per category — deterministic
         `score_value`s always win)
       - `EarlyWarningService.identify_early_warning_indicators`/
         `.identify_red_flags`, merged with the AI's own equivalents
       - `MonitoringRecommendationService.recommend_monitoring`/
         `.suggest_escalation`/`.suggest_follow_up`, merged with the
         AI's own equivalents
       - `RiskExplanationService.build_clinical_reasoning` (falls back to
         a synthesized summary when the AI wrote none)
       - `EarlyWarningService.apply_deterministic_floor` — this module's
         own top-level "deterministic floor/override" safety net,
         applied to `overall_risk_level` itself rather than trusting the
         AI's own reported level unconditionally (see that method's own
         docstring)
       - `MedicalReasoningAIPort.score_confidence` (confidence scoring —
         see this module's genuine reuse of
         `app.modules.medical_reasoning_ai`, documented in full in
         `container.py`'s own module docstring)
    -> audit logging (success or failure)
    -> return `GeneratedRiskStratification`

Only this module's **own** exceptions (raised by the parser/validator
steps) are caught and turned into an audit `log_failure` entry — errors
originating from AI Foundation, or from
`app.modules.medical_reasoning_ai`'s own facade, during `generator
.generate()`/`self._medical_reasoning.score_confidence()` propagate
unwrapped and unaudited-by-this-module, the same reasoning every prior
AI module's own use case documents for itself.
"""

from dataclasses import replace

from app.modules.medical_reasoning_ai.public.interfaces import MedicalReasoningAIPort
from app.modules.risk_stratification_ai.application.dto import GeneratedRiskStratification
from app.modules.risk_stratification_ai.application.ports import (
    RiskStratificationAnalysisAuditLoggerPort,
    RiskStratificationAnalysisGeneratorPort,
    RiskStratificationAnalysisParserPort,
    RiskStratificationAnalysisValidatorPort,
)
from app.modules.risk_stratification_ai.application.services._dedupe import (
    dedupe_preserving_order,
)
from app.modules.risk_stratification_ai.application.services.clinical_risk_assessment_service import (  # noqa: E501
    ClinicalRiskAssessmentService,
)
from app.modules.risk_stratification_ai.application.services.early_warning_service import (
    EarlyWarningService,
)
from app.modules.risk_stratification_ai.application.services.monitoring_recommendation_service import (  # noqa: E501
    MonitoringRecommendationService,
)
from app.modules.risk_stratification_ai.application.services.risk_explanation_service import (
    RiskExplanationService,
)
from app.modules.risk_stratification_ai.application.services.risk_scoring_service import (
    RiskScoringService,
)
from app.modules.risk_stratification_ai.domain.exceptions import (
    HallucinatedRiskFactorError,
    InvalidRiskConfidenceValueError,
    InvalidRiskScoreError,
    InvalidRiskStratificationResponseFormatError,
)
from app.modules.risk_stratification_ai.domain.value_objects import (
    RiskStratificationInput,
    RiskStratificationResult,
)
from app.shared.application.use_case import UseCase

_LOCAL_PIPELINE_ERRORS = (
    InvalidRiskStratificationResponseFormatError,
    InvalidRiskScoreError,
    HallucinatedRiskFactorError,
    InvalidRiskConfidenceValueError,
)


class AnalyzePatientRiskUseCase(UseCase[RiskStratificationInput, GeneratedRiskStratification]):
    def __init__(
        self,
        *,
        generator: RiskStratificationAnalysisGeneratorPort,
        parser: RiskStratificationAnalysisParserPort,
        validator: RiskStratificationAnalysisValidatorPort,
        risk_scoring_service: RiskScoringService,
        clinical_risk_assessment_service: ClinicalRiskAssessmentService,
        early_warning_service: EarlyWarningService,
        risk_explanation_service: RiskExplanationService,
        monitoring_recommendation_service: MonitoringRecommendationService,
        medical_reasoning: MedicalReasoningAIPort,
        audit_logger: RiskStratificationAnalysisAuditLoggerPort,
    ) -> None:
        self._generator = generator
        self._parser = parser
        self._validator = validator
        self._risk_scoring_service = risk_scoring_service
        self._clinical_risk_assessment_service = clinical_risk_assessment_service
        self._early_warning_service = early_warning_service
        self._risk_explanation_service = risk_explanation_service
        self._monitoring_recommendation_service = monitoring_recommendation_service
        self._medical_reasoning = medical_reasoning
        self._audit_logger = audit_logger

    async def execute(self, input_dto: RiskStratificationInput) -> GeneratedRiskStratification:
        raw_text, session = await self._generator.generate(input_dto)

        try:
            result = self._parser.parse(raw_text, output_format=input_dto.output_format)
            self._validator.validate(result, input_dto)
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
        return GeneratedRiskStratification(result=enriched_result, session=session)

    def _enrich(
        self, result: RiskStratificationResult, input_dto: RiskStratificationInput
    ) -> RiskStratificationResult:
        standardized_scores = self._risk_scoring_service.compute_standardized_scores(
            input_dto.vital_signs, input_dto.lab_values
        )
        qualitative_scores = self._clinical_risk_assessment_service.assess_qualitative_risks(
            diagnoses=input_dto.diagnoses,
            medical_history=input_dto.medical_history,
            current_medications=input_dto.current_medications,
            lab_values=input_dto.lab_values,
            patient_age=input_dto.patient_age,
        )
        deterministic_scores = standardized_scores + qualitative_scores
        merged_scores = self._risk_explanation_service.merge_risk_scores(
            result.risk_scores, deterministic_scores
        )

        early_warning_indicators = dedupe_preserving_order(
            result.early_warning_indicators
            + self._early_warning_service.identify_early_warning_indicators(input_dto.vital_signs)
        )
        red_flag_alerts = dedupe_preserving_order(
            result.red_flag_alerts
            + self._early_warning_service.identify_red_flags(input_dto.vital_signs, merged_scores)
        )
        recommended_monitoring = dedupe_preserving_order(
            result.recommended_monitoring
            + self._monitoring_recommendation_service.recommend_monitoring(merged_scores)
        )
        suggested_escalation = dedupe_preserving_order(
            result.suggested_escalation
            + self._monitoring_recommendation_service.suggest_escalation(merged_scores)
        )
        suggested_follow_up = dedupe_preserving_order(
            result.suggested_follow_up
            + self._monitoring_recommendation_service.suggest_follow_up(merged_scores)
        )
        clinical_reasoning = self._risk_explanation_service.build_clinical_reasoning(
            result.clinical_reasoning, merged_scores
        )
        overall_risk_level = self._early_warning_service.apply_deterministic_floor(
            result.overall_risk_level, merged_scores
        )

        confidence_score = self._medical_reasoning.score_confidence(
            ai_reported=result.confidence_score,
            supporting_count=len(merged_scores),
            contradicting_count=0,
            missing_information_count=0,
        )

        return replace(
            result,
            overall_risk_level=overall_risk_level,
            risk_scores=merged_scores,
            early_warning_indicators=early_warning_indicators,
            recommended_monitoring=recommended_monitoring,
            suggested_escalation=suggested_escalation,
            suggested_follow_up=suggested_follow_up,
            red_flag_alerts=red_flag_alerts,
            clinical_reasoning=clinical_reasoning,
            confidence_score=confidence_score,
        )
