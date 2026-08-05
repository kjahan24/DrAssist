"""`GeneratePatientEducationUseCase` — orchestrates the pipeline this
task specifies:

    (input already validated by
     `PatientEducationInput.__post_init__`)
    -> `PatientEducationAnalysisGeneratorPort.generate` (prompt
       selection, prompt rendering, provider selection, and the LLM call
       all happen inside this one port call — see `infrastructure
       /generation/patient_education_generator.py`)
    -> `PatientEducationAnalysisParserPort.parse` (raw AI text ->
       structured `PatientEducationResult`)
    -> `PatientEducationAnalysisValidatorPort.validate` (hallucinated
       recommendations/unsafe instructions/invalid confidence)
    -> enrichment, entirely non-throwing, applied only after the AI's own
       output has already passed validation:
       - `PatientEducationService.build_diagnosis_explanation` (used
         only when the AI's own explanation is blank)/
         `.collect_warning_signs`/`.collect_emergency_symptoms`, merged
         with the AI's own equivalents
       - `DischargeInstructionService.collect_medication_instructions`/
         `.collect_home_care_plan`/`.collect_patient_checklist`, merged
         with the AI's own equivalents
       - `LifestyleRecommendationService.collect_lifestyle_advice`/
         `.collect_diet_advice`/`.collect_exercise_advice`, merged with
         the AI's own equivalents
       - `LifestyleRecommendationService
         .collect_preventive_care_recommendations`, merged into
         `follow_up_plan` (see that service's own docstring for why)
       - `MedicalReasoningAIPort.score_confidence` (confidence scoring —
         see this module's genuine reuse of
         `app.modules.medical_reasoning_ai`, documented in full in
         `container.py`'s own module docstring)
    -> audit logging (success or failure)
    -> return `GeneratedPatientEducation`

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
from app.modules.patient_education_ai.application.dto import GeneratedPatientEducation
from app.modules.patient_education_ai.application.ports import (
    PatientEducationAnalysisAuditLoggerPort,
    PatientEducationAnalysisGeneratorPort,
    PatientEducationAnalysisParserPort,
    PatientEducationAnalysisValidatorPort,
)
from app.modules.patient_education_ai.application.services._dedupe import (
    dedupe_preserving_order,
)
from app.modules.patient_education_ai.application.services.discharge_instruction_service import (
    DischargeInstructionService,
)
from app.modules.patient_education_ai.application.services.lifestyle_recommendation_service import (  # noqa: E501
    LifestyleRecommendationService,
)
from app.modules.patient_education_ai.application.services.patient_education_service import (
    PatientEducationService,
)
from app.modules.patient_education_ai.domain.exceptions import (
    HallucinatedRecommendationError,
    InvalidPatientEducationConfidenceValueError,
    InvalidPatientEducationResponseFormatError,
    UnsafeInstructionError,
)
from app.modules.patient_education_ai.domain.value_objects import (
    PatientEducationInput,
    PatientEducationResult,
)
from app.shared.application.use_case import UseCase

_LOCAL_PIPELINE_ERRORS = (
    InvalidPatientEducationResponseFormatError,
    HallucinatedRecommendationError,
    UnsafeInstructionError,
    InvalidPatientEducationConfidenceValueError,
)


class GeneratePatientEducationUseCase(UseCase[PatientEducationInput, GeneratedPatientEducation]):
    def __init__(
        self,
        *,
        generator: PatientEducationAnalysisGeneratorPort,
        parser: PatientEducationAnalysisParserPort,
        validator: PatientEducationAnalysisValidatorPort,
        patient_education_service: PatientEducationService,
        discharge_instruction_service: DischargeInstructionService,
        lifestyle_recommendation_service: LifestyleRecommendationService,
        medical_reasoning: MedicalReasoningAIPort,
        audit_logger: PatientEducationAnalysisAuditLoggerPort,
    ) -> None:
        self._generator = generator
        self._parser = parser
        self._validator = validator
        self._patient_education_service = patient_education_service
        self._discharge_instruction_service = discharge_instruction_service
        self._lifestyle_recommendation_service = lifestyle_recommendation_service
        self._medical_reasoning = medical_reasoning
        self._audit_logger = audit_logger

    async def execute(self, input_dto: PatientEducationInput) -> GeneratedPatientEducation:
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
        return GeneratedPatientEducation(result=enriched_result, session=session)

    def _enrich(
        self, result: PatientEducationResult, input_dto: PatientEducationInput
    ) -> PatientEducationResult:
        diagnoses = input_dto.diagnoses

        diagnosis_explanation = (
            result.diagnosis_explanation.strip()
            or self._patient_education_service.build_diagnosis_explanation(diagnoses)
        )
        warning_signs = dedupe_preserving_order(
            result.warning_signs + self._patient_education_service.collect_warning_signs(diagnoses)
        )
        emergency_instructions = dedupe_preserving_order(
            result.emergency_instructions
            + self._patient_education_service.collect_emergency_symptoms(diagnoses)
        )

        medication_instructions = dedupe_preserving_order(
            result.medication_instructions
            + self._discharge_instruction_service.collect_medication_instructions(
                input_dto.current_medications
            )
        )
        home_care_plan = dedupe_preserving_order(
            result.home_care_plan
            + self._discharge_instruction_service.collect_home_care_plan(diagnoses)
        )
        patient_checklist = dedupe_preserving_order(
            result.patient_checklist
            + self._discharge_instruction_service.collect_patient_checklist(diagnoses)
        )

        lifestyle_advice = dedupe_preserving_order(
            result.lifestyle_advice
            + self._lifestyle_recommendation_service.collect_lifestyle_advice(diagnoses)
        )
        diet_advice = dedupe_preserving_order(
            result.diet_advice
            + self._lifestyle_recommendation_service.collect_diet_advice(diagnoses)
        )
        exercise_advice = dedupe_preserving_order(
            result.exercise_advice
            + self._lifestyle_recommendation_service.collect_exercise_advice(diagnoses)
        )
        follow_up_plan = dedupe_preserving_order(
            result.follow_up_plan
            + self._lifestyle_recommendation_service.collect_preventive_care_recommendations(
                diagnoses, input_dto.patient_age
            )
        )

        confidence_score = self._medical_reasoning.score_confidence(
            ai_reported=result.confidence_score,
            supporting_count=len(medication_instructions) + len(warning_signs),
            contradicting_count=0,
            missing_information_count=0,
        )

        return replace(
            result,
            diagnosis_explanation=diagnosis_explanation,
            medication_instructions=medication_instructions,
            home_care_plan=home_care_plan,
            lifestyle_advice=lifestyle_advice,
            diet_advice=diet_advice,
            exercise_advice=exercise_advice,
            warning_signs=warning_signs,
            emergency_instructions=emergency_instructions,
            follow_up_plan=follow_up_plan,
            patient_checklist=patient_checklist,
            confidence_score=confidence_score,
        )
