"""`InterpretRadiologyReportUseCase` — orchestrates the pipeline this
task specifies:

    (input already validated by
     `RadiologyInterpretationInput.__post_init__`)
    -> `RadiologyInterpreterPort.generate` (prompt selection, prompt
       rendering, provider selection, and the LLM call all happen inside
       this one port call — see `infrastructure/generation
       /radiology_interpretation_generator.py`)
    -> `RadiologyInterpretationParserPort.parse` (raw AI text -> structured
       `RadiologyInterpretationResult`)
    -> `RadiologyInterpretationValidatorPort.validate` (duplicated-findings/
       hallucinated-findings/inconsistent-recommendations/invalid-
       confidence-value)
    -> enrichment, entirely non-throwing, applied only after the AI's own
       output has already passed validation:
       - `FindingExtractionService.extract` computes the deterministic
         candidate-finding pool for this report exactly once
       - `CriticalFindingDetectionService.escalate_on_critical_keywords`
         (severity-misclassification safety net)
       - `CriticalFindingDetectionService.derive_findings_missed_by_ai`,
         merged into `findings` (omission safety net)
       - `FollowUpRecommendationService.derive_follow_up_for_critical_findings`/
         `.derive_specialist_referral_for_critical_findings`, merged into
         `suggested_follow_up_imaging`/`suggested_specialist_referral`
       - `FollowUpRecommendationService.deduplicate`, applied defensively
         to every list-shaped output field
       - `MedicalReasoningAIPort.score_confidence` (confidence scoring —
         see this module's genuine reuse of
         `app.modules.medical_reasoning_ai`, documented in full in
         `container.py`'s own module docstring)
    -> audit logging (success or failure)
    -> return `GeneratedRadiologyInterpretation`

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
from app.modules.radiology_interpretation_ai.application.dto import (
    GeneratedRadiologyInterpretation,
)
from app.modules.radiology_interpretation_ai.application.ports import (
    RadiologyInterpretationAuditLoggerPort,
    RadiologyInterpretationParserPort,
    RadiologyInterpretationValidatorPort,
    RadiologyInterpreterPort,
)
from app.modules.radiology_interpretation_ai.application.services.critical_finding_detection_service import (  # noqa: E501
    CriticalFindingDetectionService,
)
from app.modules.radiology_interpretation_ai.application.services.finding_extraction_service import (  # noqa: E501
    FindingExtractionService,
)
from app.modules.radiology_interpretation_ai.application.services.follow_up_recommendation_service import (  # noqa: E501
    FollowUpRecommendationService,
)
from app.modules.radiology_interpretation_ai.domain.exceptions import (
    DuplicateRadiologyFindingError,
    HallucinatedRadiologyFindingError,
    InconsistentRadiologyRecommendationsError,
    InvalidRadiologyConfidenceValueError,
    InvalidRadiologyInterpretationResponseFormatError,
)
from app.modules.radiology_interpretation_ai.domain.value_objects import (
    RadiologyInterpretationInput,
    RadiologyInterpretationResult,
)
from app.shared.application.use_case import UseCase

_LOCAL_PIPELINE_ERRORS = (
    InvalidRadiologyInterpretationResponseFormatError,
    DuplicateRadiologyFindingError,
    HallucinatedRadiologyFindingError,
    InconsistentRadiologyRecommendationsError,
    InvalidRadiologyConfidenceValueError,
)


class InterpretRadiologyReportUseCase(
    UseCase[RadiologyInterpretationInput, GeneratedRadiologyInterpretation]
):
    def __init__(
        self,
        *,
        generator: RadiologyInterpreterPort,
        parser: RadiologyInterpretationParserPort,
        validator: RadiologyInterpretationValidatorPort,
        finding_extraction_service: FindingExtractionService,
        critical_finding_service: CriticalFindingDetectionService,
        recommendation_service: FollowUpRecommendationService,
        medical_reasoning: MedicalReasoningAIPort,
        audit_logger: RadiologyInterpretationAuditLoggerPort,
    ) -> None:
        self._generator = generator
        self._parser = parser
        self._validator = validator
        self._finding_extraction_service = finding_extraction_service
        self._critical_finding_service = critical_finding_service
        self._recommendation_service = recommendation_service
        self._medical_reasoning = medical_reasoning
        self._audit_logger = audit_logger

    async def execute(
        self, input_dto: RadiologyInterpretationInput
    ) -> GeneratedRadiologyInterpretation:
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
        return GeneratedRadiologyInterpretation(result=enriched_result, session=session)

    def _enrich(
        self, result: RadiologyInterpretationResult, input_dto: RadiologyInterpretationInput
    ) -> RadiologyInterpretationResult:
        candidates = self._finding_extraction_service.extract(input_dto.report_text)

        escalated_findings = self._critical_finding_service.escalate_on_critical_keywords(
            result.findings
        )
        missed_findings = self._critical_finding_service.derive_findings_missed_by_ai(
            candidates=candidates, ai_findings=escalated_findings
        )
        reconciled_findings = escalated_findings + missed_findings

        derived_follow_up = self._recommendation_service.derive_follow_up_for_critical_findings(
            reconciled_findings
        )
        merged_follow_up = self._recommendation_service.deduplicate(
            result.suggested_follow_up_imaging + derived_follow_up
        )

        derived_referral = (
            self._recommendation_service.derive_specialist_referral_for_critical_findings(
                reconciled_findings
            )
        )
        merged_referral = self._recommendation_service.deduplicate(
            result.suggested_specialist_referral + derived_referral
        )

        merged_differential = self._recommendation_service.deduplicate(
            result.differential_imaging_considerations
        )
        merged_red_flags = self._recommendation_service.deduplicate(result.red_flag_warnings)

        confidence_score = self._medical_reasoning.score_confidence(
            ai_reported=result.confidence_score,
            supporting_count=len(reconciled_findings),
            contradicting_count=0,
            missing_information_count=0,
        )

        return replace(
            result,
            findings=reconciled_findings,
            differential_imaging_considerations=merged_differential,
            suggested_follow_up_imaging=merged_follow_up,
            suggested_specialist_referral=merged_referral,
            red_flag_warnings=merged_red_flags,
            confidence_score=confidence_score,
        )
