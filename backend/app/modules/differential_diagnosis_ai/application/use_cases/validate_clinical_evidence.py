"""`ValidateClinicalEvidenceUseCase` — an advisory, non-throwing "pre-
flight" check distinct from `DifferentialDiagnosisInput.__post_init__`'s
structural (Tier 3) validation, the same shape
`app.modules.prescription_ai.application.use_cases
.validate_prescription_context.ValidatePrescriptionContextUseCase`
establishes for its own module. Flags completeness concerns a caller may
want to surface before spending a real generation call — differential
diagnosis quality depends heavily on the breadth of clinical evidence
supplied, so this delegates most of its "missing information" reasoning
to `ClinicalReasoningService.assess_missing_information`
(`ClinicalReasoningPort`'s own docstring explains why that lives here
rather than in the generation pipeline), plus a handful of module-
specific completeness warnings.
"""

from app.modules.differential_diagnosis_ai.application.dto import (
    ClinicalEvidenceValidationResultDTO,
)
from app.modules.differential_diagnosis_ai.application.services.clinical_reasoning_service import (
    ClinicalReasoningService,
)
from app.modules.differential_diagnosis_ai.domain.value_objects import DifferentialDiagnosisInput
from app.shared.application.use_case import UseCase


class ValidateClinicalEvidenceUseCase(
    UseCase[DifferentialDiagnosisInput, ClinicalEvidenceValidationResultDTO]
):
    def __init__(self, *, reasoning_service: ClinicalReasoningService) -> None:
        self._reasoning_service = reasoning_service

    async def execute(
        self, input_dto: DifferentialDiagnosisInput
    ) -> ClinicalEvidenceValidationResultDTO:
        warnings = list(self._reasoning_service.assess_missing_information(input_dto))

        if not input_dto.allergies:
            warnings.append("no allergy information provided")

        if not input_dto.medical_conditions:
            warnings.append("no medical conditions provided")

        return ClinicalEvidenceValidationResultDTO(
            is_valid=True, errors=(), warnings=tuple(warnings)
        )
