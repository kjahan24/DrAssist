"""`ValidateSOAPInputUseCase` — an advisory, non-throwing "pre-flight"
check distinct from `SOAPEncounterInput.__post_init__`'s structural
(Tier 3) validation, the same shape
`app.modules.clinical_note_ai.application.use_cases
.validate_clinical_input.ValidateClinicalInputUseCase` establishes for
its own module. Flags completeness concerns (missing HPI/ROS/exam/
assessment/plan) a caller may want to surface before spending a real
generation call.
"""

from app.modules.soap_note_ai.application.dto import SOAPValidationResultDTO
from app.modules.soap_note_ai.domain.value_objects import SOAPEncounterInput
from app.shared.application.use_case import UseCase


class ValidateSOAPInputUseCase(UseCase[SOAPEncounterInput, SOAPValidationResultDTO]):
    async def execute(self, input_dto: SOAPEncounterInput) -> SOAPValidationResultDTO:
        warnings: list[str] = []

        has_subjective_content = bool(
            (input_dto.history_of_present_illness or "").strip()
            or input_dto.symptoms
            or (input_dto.review_of_systems or "").strip()
        )
        if not has_subjective_content:
            warnings.append(
                "no history of present illness, symptoms, or review of systems provided "
                "— the generated Subjective section may be thin"
            )

        has_objective_content = bool(
            (input_dto.physical_examination or "").strip() or input_dto.vitals
        )
        if not has_objective_content:
            warnings.append("no physical examination findings or vitals provided")

        if not (input_dto.assessment or "").strip() and not input_dto.diagnoses:
            warnings.append("no assessment or diagnoses provided")

        if not (input_dto.plan or "").strip():
            warnings.append("no plan provided")

        return SOAPValidationResultDTO(is_valid=True, errors=(), warnings=tuple(warnings))
