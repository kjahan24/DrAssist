"""`ValidateClinicalContextUseCase` — an advisory, non-throwing "pre-
flight" check distinct from `ICD10CodingInput.__post_init__`'s structural
(Tier 3) validation, the same shape
`app.modules.soap_note_ai.application.use_cases.validate_soap_input
.ValidateSOAPInputUseCase` establishes for its own module. Flags
completeness concerns (missing clinical detail, no existing diagnoses or
clinical/SOAP note context) a caller may want to surface before spending
a real generation call — coding suggestions from a bare chief complaint
alone are far less reliable than ones grounded in HPI/assessment/notes.
"""

from app.modules.icd10_ai.application.dto import ClinicalContextValidationResultDTO
from app.modules.icd10_ai.domain.value_objects import ICD10CodingInput
from app.shared.application.use_case import UseCase


class ValidateClinicalContextUseCase(UseCase[ICD10CodingInput, ClinicalContextValidationResultDTO]):
    async def execute(self, input_dto: ICD10CodingInput) -> ClinicalContextValidationResultDTO:
        warnings: list[str] = []

        has_narrative_content = bool(
            (input_dto.history_of_present_illness or "").strip()
            or input_dto.symptoms
            or (input_dto.review_of_systems or "").strip()
            or (input_dto.physical_examination or "").strip()
        )
        if not has_narrative_content:
            warnings.append(
                "no HPI, symptoms, review of systems, or physical examination provided "
                "— coding suggestions grounded only in the chief complaint may be unreliable"
            )

        has_clinical_summary = bool(
            (input_dto.assessment or "").strip()
            or (input_dto.plan or "").strip()
            or (input_dto.clinical_note or "").strip()
            or (input_dto.soap_note or "").strip()
        )
        if not has_clinical_summary:
            warnings.append(
                "no assessment, plan, clinical note, or SOAP note provided "
                "— consider supplying one for higher-confidence coding"
            )

        if not input_dto.existing_diagnoses:
            warnings.append("no existing diagnoses provided")

        return ClinicalContextValidationResultDTO(
            is_valid=True, errors=(), warnings=tuple(warnings)
        )
