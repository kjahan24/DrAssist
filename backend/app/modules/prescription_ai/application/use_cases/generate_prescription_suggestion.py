"""`GeneratePrescriptionSuggestionUseCase` — orchestrates the pipeline
this task specifies:

    (input already validated by `PrescriptionContextInput.__post_init__`)
    -> `PrescriptionGeneratorPort.generate` (prompt selection, prompt
       rendering, provider selection, and the LLM call all happen inside
       this one port call — see `infrastructure/generation
       /prescription_generator.py`)
    -> `PrescriptionSuggestionParserPort.parse` (raw AI text -> structured
       `PrescriptionSuggestionSet`, including the AI's own self-reported
       safety findings)
    -> `PrescriptionSuggestionValidatorPort.validate` (empty/malformed
       structure/duplicate/missing dosage-frequency-duration/
       hallucinated medications)
    -> `MedicationSafetyAnalysisService.analyze` (the deterministic half
       of medication safety — drug interactions, allergy conflicts,
       duplicate therapy) run against the now-validated medication list,
       merged with the AI's own self-reported `safety_findings`
    -> audit logging (success or failure)
    -> return `GeneratedPrescriptionSuggestions`

Only this module's **own** exceptions (raised by the parser/validator
steps) are caught and turned into an audit `log_failure` entry — errors
originating from AI Foundation during `generator.generate()` propagate
unwrapped and unaudited-by-this-module, the same reasoning
`app.modules.icd10_ai.application.use_cases.generate_icd10_suggestions
.GenerateICD10SuggestionsUseCase` documents for itself. The deterministic
safety analysis never raises (it only appends findings), so it sits
outside the try/except entirely, the same "sits outside the try/except"
placement that module's own ranking step uses.
"""

from dataclasses import replace

from app.modules.prescription_ai.application.dto import GeneratedPrescriptionSuggestions
from app.modules.prescription_ai.application.ports import (
    PrescriptionAuditLoggerPort,
    PrescriptionGeneratorPort,
    PrescriptionSuggestionParserPort,
    PrescriptionSuggestionValidatorPort,
)
from app.modules.prescription_ai.application.services.medication_safety_analysis_service import (
    MedicationSafetyAnalysisService,
)
from app.modules.prescription_ai.domain.exceptions import (
    DuplicateMedicationError,
    EmptyPrescriptionResponseError,
    HallucinatedMedicationError,
    InvalidMedicationStructureError,
    InvalidPrescriptionResponseFormatError,
    MissingMedicationDosageError,
    MissingMedicationDurationError,
    MissingMedicationFrequencyError,
)
from app.modules.prescription_ai.domain.value_objects import (
    MedicationSafetyFinding,
    PrescriptionContextInput,
)
from app.shared.application.use_case import UseCase

_LOCAL_PIPELINE_ERRORS = (
    InvalidPrescriptionResponseFormatError,
    EmptyPrescriptionResponseError,
    InvalidMedicationStructureError,
    DuplicateMedicationError,
    MissingMedicationDosageError,
    MissingMedicationFrequencyError,
    MissingMedicationDurationError,
    HallucinatedMedicationError,
)


class GeneratePrescriptionSuggestionUseCase(
    UseCase[PrescriptionContextInput, GeneratedPrescriptionSuggestions]
):
    def __init__(
        self,
        *,
        generator: PrescriptionGeneratorPort,
        parser: PrescriptionSuggestionParserPort,
        validator: PrescriptionSuggestionValidatorPort,
        safety_service: MedicationSafetyAnalysisService,
        audit_logger: PrescriptionAuditLoggerPort,
    ) -> None:
        self._generator = generator
        self._parser = parser
        self._validator = validator
        self._safety_service = safety_service
        self._audit_logger = audit_logger

    async def execute(
        self, input_dto: PrescriptionContextInput
    ) -> GeneratedPrescriptionSuggestions:
        raw_text, session = await self._generator.generate(input_dto)

        try:
            suggestion_set = self._parser.parse(raw_text, output_format=input_dto.output_format)
            self._validator.validate(suggestion_set)
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

        deterministic_findings = self._safety_service.analyze(
            medications=suggestion_set.medications,
            existing_medications=input_dto.existing_medications,
            allergies=input_dto.allergies,
        )
        merged = self._merge_findings(suggestion_set.safety_findings, deterministic_findings)
        enriched_set = replace(suggestion_set, safety_findings=merged)

        await self._audit_logger.log_generation(
            session, organization_id=input_dto.organization_id, patient_id=input_dto.patient_id
        )
        return GeneratedPrescriptionSuggestions(suggestions=enriched_set, session=session)

    def _merge_findings(
        self,
        ai_reported: tuple[MedicationSafetyFinding, ...],
        deterministic: tuple[MedicationSafetyFinding, ...],
    ) -> tuple[MedicationSafetyFinding, ...]:
        seen: set[tuple[str, str, tuple[str, ...]]] = set()
        merged: list[MedicationSafetyFinding] = []
        for finding in (*ai_reported, *deterministic):
            key = (
                finding.category.value,
                finding.description.strip().lower(),
                tuple(sorted(m.strip().lower() for m in finding.affected_medications)),
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(finding)
        return tuple(merged)
