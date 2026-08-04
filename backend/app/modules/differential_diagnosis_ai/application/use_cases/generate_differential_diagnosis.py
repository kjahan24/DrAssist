"""`GenerateDifferentialDiagnosisUseCase` — orchestrates the pipeline
this task specifies:

    (input already validated by `DifferentialDiagnosisInput.__post_init__`)
    -> `DifferentialDiagnosisGeneratorPort.generate` (prompt selection,
       prompt rendering, provider selection, and the LLM call all happen
       inside this one port call — see `infrastructure/generation
       /differential_diagnosis_generator.py`)
    -> `DifferentialDiagnosisParserPort.parse` (raw AI text -> structured
       `DifferentialDiagnosisResult`)
    -> `DifferentialDiagnosisValidatorPort.validate` (empty/duplicate/
       invalid confidence/invalid ranking/hallucinated/inconsistent
       reasoning)
    -> `ClinicalReasoningService.upgrade_urgency_levels` (the
       deterministic half of "urgency classification" — a safety floor
       applied only after the AI's own output has already passed
       validation)
    -> `DifferentialDiagnosisRankingService.rank` (the "confidence
       ranking" clinical-reasoning requirement, applied as the final
       pipeline step so callers receive an already-ordered result)
    -> audit logging (success or failure)
    -> return `GeneratedDifferentialDiagnosis`

Only this module's **own** exceptions (raised by the parser/validator
steps) are caught and turned into an audit `log_failure` entry — errors
originating from AI Foundation during `generator.generate()` propagate
unwrapped and unaudited-by-this-module, the same reasoning
`app.modules.prescription_ai.application.use_cases
.generate_prescription_suggestion.GeneratePrescriptionSuggestionUseCase`
documents for itself. Urgency-upgrading and ranking never raise (they
only transform already-validated data), so both sit outside the
try/except entirely.
"""

from dataclasses import replace

from app.modules.differential_diagnosis_ai.application.dto import GeneratedDifferentialDiagnosis
from app.modules.differential_diagnosis_ai.application.ports import (
    DifferentialDiagnosisAuditLoggerPort,
    DifferentialDiagnosisGeneratorPort,
    DifferentialDiagnosisParserPort,
    DifferentialDiagnosisValidatorPort,
)
from app.modules.differential_diagnosis_ai.application.services.clinical_reasoning_service import (
    ClinicalReasoningService,
)
from app.modules.differential_diagnosis_ai.application.services.differential_diagnosis_ranking_service import (  # noqa: E501
    DifferentialDiagnosisRankingService,
)
from app.modules.differential_diagnosis_ai.domain.exceptions import (
    DuplicateDiagnosisError,
    EmptyDifferentialResponseError,
    HallucinatedDiagnosisError,
    InconsistentReasoningError,
    InvalidConfidenceScoreError,
    InvalidDifferentialResponseFormatError,
    InvalidRankingError,
)
from app.modules.differential_diagnosis_ai.domain.value_objects import DifferentialDiagnosisInput
from app.shared.application.use_case import UseCase

_LOCAL_PIPELINE_ERRORS = (
    InvalidDifferentialResponseFormatError,
    EmptyDifferentialResponseError,
    DuplicateDiagnosisError,
    InvalidConfidenceScoreError,
    InvalidRankingError,
    HallucinatedDiagnosisError,
    InconsistentReasoningError,
)


class GenerateDifferentialDiagnosisUseCase(
    UseCase[DifferentialDiagnosisInput, GeneratedDifferentialDiagnosis]
):
    def __init__(
        self,
        *,
        generator: DifferentialDiagnosisGeneratorPort,
        parser: DifferentialDiagnosisParserPort,
        validator: DifferentialDiagnosisValidatorPort,
        reasoning_service: ClinicalReasoningService,
        ranking_service: DifferentialDiagnosisRankingService,
        audit_logger: DifferentialDiagnosisAuditLoggerPort,
    ) -> None:
        self._generator = generator
        self._parser = parser
        self._validator = validator
        self._reasoning_service = reasoning_service
        self._ranking_service = ranking_service
        self._audit_logger = audit_logger

    async def execute(
        self, input_dto: DifferentialDiagnosisInput
    ) -> GeneratedDifferentialDiagnosis:
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

        upgraded_candidates = self._reasoning_service.upgrade_urgency_levels(result.candidates)
        enriched_result = replace(result, candidates=upgraded_candidates)
        ranked_result = self._ranking_service.rank(enriched_result)

        await self._audit_logger.log_generation(
            session, organization_id=input_dto.organization_id, patient_id=input_dto.patient_id
        )
        return GeneratedDifferentialDiagnosis(result=ranked_result, session=session)
