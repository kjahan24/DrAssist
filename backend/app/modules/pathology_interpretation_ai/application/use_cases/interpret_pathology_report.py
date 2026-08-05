"""`InterpretPathologyReportUseCase` — orchestrates the pipeline this
task specifies:

    (input already validated by
     `PathologyInterpretationInput.__post_init__`)
    -> `PathologyInterpreterPort.generate` (prompt selection, prompt
       rendering, provider selection, and the LLM call all happen inside
       this one port call — see `infrastructure/generation
       /pathology_interpretation_generator.py`)
    -> `PathologyInterpretationParserPort.parse` (raw AI text ->
       structured `PathologyInterpretationResult`)
    -> `PathologyInterpretationValidatorPort.validate` (duplicated-
       findings/hallucinated-findings/inconsistent-conclusions/invalid-
       confidence-value)
    -> enrichment, entirely non-throwing, applied only after the AI's own
       output has already passed validation:
       - `FindingExtractionService.extract` computes the deterministic
         candidate-finding pool for this report exactly once
       - `MalignancyAssessmentService.escalate_on_malignant_keywords`
         (severity-misclassification safety net)
       - `MalignancyAssessmentService.derive_findings_missed_by_ai`,
         merged into `microscopic_findings` (omission safety net)
       - `ClinicalCorrelationService.derive_correlation_recommendations_for_malignant_findings`/
         `.derive_follow_up_for_malignant_findings`/
         `.derive_specialist_referral_for_malignant_findings`, merged
         into `correlation_recommendations`/`suggested_follow_up`/
         `suggested_specialist_referral`
       - `ClinicalCorrelationService.deduplicate`, applied defensively to
         every list-shaped output field
       - `MedicalReasoningAIPort.score_confidence` (confidence scoring —
         see this module's genuine reuse of
         `app.modules.medical_reasoning_ai`, documented in full in
         `container.py`'s own module docstring)
    -> audit logging (success or failure)
    -> return `GeneratedPathologyInterpretation`

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
from app.modules.pathology_interpretation_ai.application.dto import (
    GeneratedPathologyInterpretation,
)
from app.modules.pathology_interpretation_ai.application.ports import (
    PathologyInterpretationAuditLoggerPort,
    PathologyInterpretationParserPort,
    PathologyInterpretationValidatorPort,
    PathologyInterpreterPort,
)
from app.modules.pathology_interpretation_ai.application.services.clinical_correlation_service import (  # noqa: E501
    ClinicalCorrelationService,
)
from app.modules.pathology_interpretation_ai.application.services.finding_extraction_service import (  # noqa: E501
    FindingExtractionService,
)
from app.modules.pathology_interpretation_ai.application.services.malignancy_assessment_service import (  # noqa: E501
    MalignancyAssessmentService,
)
from app.modules.pathology_interpretation_ai.domain.exceptions import (
    DuplicatePathologyFindingError,
    HallucinatedPathologyFindingError,
    InconsistentPathologyConclusionsError,
    InvalidPathologyConfidenceValueError,
    InvalidPathologyInterpretationResponseFormatError,
)
from app.modules.pathology_interpretation_ai.domain.value_objects import (
    PathologyInterpretationInput,
    PathologyInterpretationResult,
)
from app.shared.application.use_case import UseCase

_LOCAL_PIPELINE_ERRORS = (
    InvalidPathologyInterpretationResponseFormatError,
    DuplicatePathologyFindingError,
    HallucinatedPathologyFindingError,
    InconsistentPathologyConclusionsError,
    InvalidPathologyConfidenceValueError,
)


class InterpretPathologyReportUseCase(
    UseCase[PathologyInterpretationInput, GeneratedPathologyInterpretation]
):
    def __init__(
        self,
        *,
        generator: PathologyInterpreterPort,
        parser: PathologyInterpretationParserPort,
        validator: PathologyInterpretationValidatorPort,
        finding_extraction_service: FindingExtractionService,
        malignancy_assessment_service: MalignancyAssessmentService,
        correlation_service: ClinicalCorrelationService,
        medical_reasoning: MedicalReasoningAIPort,
        audit_logger: PathologyInterpretationAuditLoggerPort,
    ) -> None:
        self._generator = generator
        self._parser = parser
        self._validator = validator
        self._finding_extraction_service = finding_extraction_service
        self._malignancy_assessment_service = malignancy_assessment_service
        self._correlation_service = correlation_service
        self._medical_reasoning = medical_reasoning
        self._audit_logger = audit_logger

    async def execute(
        self, input_dto: PathologyInterpretationInput
    ) -> GeneratedPathologyInterpretation:
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
        return GeneratedPathologyInterpretation(result=enriched_result, session=session)

    def _enrich(
        self, result: PathologyInterpretationResult, input_dto: PathologyInterpretationInput
    ) -> PathologyInterpretationResult:
        candidates = self._finding_extraction_service.extract(input_dto.report_text)

        escalated_findings = self._malignancy_assessment_service.escalate_on_malignant_keywords(
            result.microscopic_findings
        )
        missed_findings = self._malignancy_assessment_service.derive_findings_missed_by_ai(
            candidates=candidates, ai_findings=escalated_findings
        )
        reconciled_findings = escalated_findings + missed_findings

        derived_correlations = (
            self._correlation_service.derive_correlation_recommendations_for_malignant_findings(
                reconciled_findings
            )
        )
        merged_correlations = self._correlation_service.deduplicate(
            result.correlation_recommendations + derived_correlations
        )

        derived_follow_up = self._correlation_service.derive_follow_up_for_malignant_findings(
            reconciled_findings
        )
        merged_follow_up = self._correlation_service.deduplicate(
            result.suggested_follow_up + derived_follow_up
        )

        derived_referral = (
            self._correlation_service.derive_specialist_referral_for_malignant_findings(
                reconciled_findings
            )
        )
        merged_referral = self._correlation_service.deduplicate(
            result.suggested_specialist_referral + derived_referral
        )

        merged_key_findings = self._correlation_service.deduplicate(result.key_findings)
        merged_red_flags = self._correlation_service.deduplicate(result.red_flag_warnings)

        confidence_score = self._medical_reasoning.score_confidence(
            ai_reported=result.confidence_score,
            supporting_count=len(reconciled_findings),
            contradicting_count=0,
            missing_information_count=0,
        )

        return replace(
            result,
            key_findings=merged_key_findings,
            microscopic_findings=reconciled_findings,
            correlation_recommendations=merged_correlations,
            suggested_follow_up=merged_follow_up,
            suggested_specialist_referral=merged_referral,
            red_flag_warnings=merged_red_flags,
            confidence_score=confidence_score,
        )
