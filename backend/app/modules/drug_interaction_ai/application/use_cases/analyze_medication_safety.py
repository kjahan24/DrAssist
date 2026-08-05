"""`AnalyzeMedicationSafetyUseCase` — orchestrates the pipeline this task
specifies:

    (input already validated by
     `DrugInteractionAnalysisInput.__post_init__`)
    -> `DrugSafetyAnalysisGeneratorPort.generate` (prompt selection,
       prompt rendering, provider selection, and the LLM call all happen
       inside this one port call — see `infrastructure/generation
       /drug_safety_analysis_generator.py`)
    -> `DrugSafetyAnalysisParserPort.parse` (raw AI text -> structured
       `DrugInteractionAnalysisResult`)
    -> `DrugSafetyAnalysisValidatorPort.validate` (unknown-medications/
       hallucinated-interactions/invalid-confidence/missing-evidence)
    -> enrichment, entirely non-throwing, applied only after the AI's own
       output has already passed validation — every one of this task's
       own eighteen DETECT categories is covered by exactly one of the
       five deterministic detection calls below (see each service's own
       module docstring for which categories it owns):
       - `DrugInteractionService.detect_known_interactions`
       - `MedicationSafetyService.detect_patient_context_risks`/
         `.detect_pharmacologic_risk_flags`/`.detect_reconciliation_issues`
       - `ContraindicationService.detect_duplicate_therapy`/
         `.detect_contraindications`/`.detect_black_box_warnings`
       - `DoseAdjustmentService.suggest_dose_adjustments`
       - all detected/AI-reported interactions are merged and then
         `DrugInteractionService.reconcile_evidence_levels`d (the
         evidence-grading safety net) before being deduplicated
       - `AlternativeMedicationService.derive_alternatives_for_high_severity_issues`,
         merged into `alternative_medication_suggestions`
       - `AlternativeMedicationService.deduplicate`/`.deduplicate_issues`,
         applied defensively to every list-shaped output field
       - `MedicalReasoningAIPort.score_confidence` (confidence scoring —
         see this module's genuine reuse of
         `app.modules.medical_reasoning_ai`, documented in full in
         `container.py`'s own module docstring)
    -> audit logging (success or failure)
    -> return `GeneratedDrugInteractionAnalysis`

Only this module's **own** exceptions (raised by the parser/validator
steps) are caught and turned into an audit `log_failure` entry — errors
originating from AI Foundation, or from
`app.modules.medical_reasoning_ai`'s own facade, during `generator
.generate()`/`self._medical_reasoning.score_confidence()` propagate
unwrapped and unaudited-by-this-module, the same reasoning every prior
AI module's own use case documents for itself.
"""

from dataclasses import replace

from app.modules.drug_interaction_ai.application.dto import GeneratedDrugInteractionAnalysis
from app.modules.drug_interaction_ai.application.ports import (
    DrugSafetyAnalysisAuditLoggerPort,
    DrugSafetyAnalysisGeneratorPort,
    DrugSafetyAnalysisParserPort,
    DrugSafetyAnalysisValidatorPort,
)
from app.modules.drug_interaction_ai.application.services.alternative_medication_service import (
    AlternativeMedicationService,
)
from app.modules.drug_interaction_ai.application.services.contraindication_service import (
    ContraindicationService,
)
from app.modules.drug_interaction_ai.application.services.dose_adjustment_service import (
    DoseAdjustmentService,
)
from app.modules.drug_interaction_ai.application.services.drug_interaction_service import (
    DrugInteractionService,
)
from app.modules.drug_interaction_ai.application.services.medication_safety_service import (
    MedicationSafetyService,
)
from app.modules.drug_interaction_ai.domain.exceptions import (
    HallucinatedInteractionError,
    InvalidDrugInteractionConfidenceValueError,
    InvalidDrugInteractionResponseFormatError,
    MissingInteractionEvidenceError,
    UnknownMedicationError,
)
from app.modules.drug_interaction_ai.domain.value_objects import (
    DrugInteractionAnalysisInput,
    DrugInteractionAnalysisResult,
    MedicationEntry,
)
from app.modules.medical_reasoning_ai.public.interfaces import MedicalReasoningAIPort
from app.shared.application.use_case import UseCase

_LOCAL_PIPELINE_ERRORS = (
    InvalidDrugInteractionResponseFormatError,
    UnknownMedicationError,
    HallucinatedInteractionError,
    InvalidDrugInteractionConfidenceValueError,
    MissingInteractionEvidenceError,
)


class AnalyzeMedicationSafetyUseCase(
    UseCase[DrugInteractionAnalysisInput, GeneratedDrugInteractionAnalysis]
):
    def __init__(
        self,
        *,
        generator: DrugSafetyAnalysisGeneratorPort,
        parser: DrugSafetyAnalysisParserPort,
        validator: DrugSafetyAnalysisValidatorPort,
        drug_interaction_service: DrugInteractionService,
        medication_safety_service: MedicationSafetyService,
        contraindication_service: ContraindicationService,
        dose_adjustment_service: DoseAdjustmentService,
        alternative_medication_service: AlternativeMedicationService,
        medical_reasoning: MedicalReasoningAIPort,
        audit_logger: DrugSafetyAnalysisAuditLoggerPort,
    ) -> None:
        self._generator = generator
        self._parser = parser
        self._validator = validator
        self._drug_interaction_service = drug_interaction_service
        self._medication_safety_service = medication_safety_service
        self._contraindication_service = contraindication_service
        self._dose_adjustment_service = dose_adjustment_service
        self._alternative_medication_service = alternative_medication_service
        self._medical_reasoning = medical_reasoning
        self._audit_logger = audit_logger

    async def execute(
        self, input_dto: DrugInteractionAnalysisInput
    ) -> GeneratedDrugInteractionAnalysis:
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
        return GeneratedDrugInteractionAnalysis(result=enriched_result, session=session)

    def _all_medications(
        self, input_dto: DrugInteractionAnalysisInput
    ) -> tuple[MedicationEntry, ...]:
        if input_dto.new_prescription is None:
            return input_dto.current_medications
        return input_dto.current_medications + (input_dto.new_prescription,)

    def _enrich(
        self, result: DrugInteractionAnalysisResult, input_dto: DrugInteractionAnalysisInput
    ) -> DrugInteractionAnalysisResult:
        all_medications = self._all_medications(input_dto)

        known_interactions = self._drug_interaction_service.detect_known_interactions(
            all_medications
        )
        patient_context_risks = self._medication_safety_service.detect_patient_context_risks(
            all_medications,
            allergies=input_dto.allergies,
            medical_conditions=input_dto.medical_conditions,
            pregnancy_status=input_dto.pregnancy_status,
            lactation_status=input_dto.lactation_status,
            patient_age=input_dto.patient_age,
        )
        pharmacologic_risk_flags = self._medication_safety_service.detect_pharmacologic_risk_flags(
            all_medications
        )
        reconciliation_issues = self._medication_safety_service.detect_reconciliation_issues(
            input_dto.current_medications
        )
        duplicate_therapy = self._contraindication_service.detect_duplicate_therapy(all_medications)

        merged_interactions_raw = (
            result.interactions
            + known_interactions
            + patient_context_risks
            + pharmacologic_risk_flags
            + reconciliation_issues
            + duplicate_therapy
        )
        reconciled_interactions = self._drug_interaction_service.reconcile_evidence_levels(
            merged_interactions_raw
        )
        deduped_interactions = self._alternative_medication_service.deduplicate_issues(
            reconciled_interactions
        )

        deterministic_contraindications = self._contraindication_service.detect_contraindications(
            all_medications
        )
        merged_contraindications = self._alternative_medication_service.deduplicate(
            result.contraindications + deterministic_contraindications
        )

        deterministic_black_box_warnings = self._contraindication_service.detect_black_box_warnings(
            all_medications
        )
        merged_warnings = self._alternative_medication_service.deduplicate(
            result.warnings + deterministic_black_box_warnings
        )

        deterministic_dose_adjustments = self._dose_adjustment_service.suggest_dose_adjustments(
            all_medications,
            renal_function=input_dto.renal_function,
            hepatic_function=input_dto.hepatic_function,
        )
        merged_dose_adjustments = self._alternative_medication_service.deduplicate(
            result.dose_adjustment_suggestions + deterministic_dose_adjustments
        )

        derived_alternatives = (
            self._alternative_medication_service.derive_alternatives_for_high_severity_issues(
                deduped_interactions
            )
        )
        merged_alternatives = self._alternative_medication_service.deduplicate(
            result.alternative_medication_suggestions + derived_alternatives
        )

        merged_monitoring = self._alternative_medication_service.deduplicate(
            result.monitoring_recommendations
        )
        merged_counseling = self._alternative_medication_service.deduplicate(
            result.patient_counseling_points
        )

        confidence_score = self._medical_reasoning.score_confidence(
            ai_reported=result.confidence_score,
            supporting_count=len(deduped_interactions),
            contradicting_count=0,
            missing_information_count=0,
        )

        return replace(
            result,
            interactions=deduped_interactions,
            contraindications=merged_contraindications,
            warnings=merged_warnings,
            monitoring_recommendations=merged_monitoring,
            dose_adjustment_suggestions=merged_dose_adjustments,
            alternative_medication_suggestions=merged_alternatives,
            patient_counseling_points=merged_counseling,
            confidence_score=confidence_score,
        )
