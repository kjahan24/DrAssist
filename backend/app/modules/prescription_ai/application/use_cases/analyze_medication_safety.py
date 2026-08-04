"""`AnalyzeMedicationSafetyUseCase` — a standalone entry point onto
`MedicationSafetyAnalysisService` for a caller that already has an
assembled medication list (e.g. a physician-edited draft, or one merged
across multiple generations) and wants deterministic safety findings
without a further AI call. `GeneratePrescriptionSuggestionUseCase` uses
the same `MedicationSafetyAnalysisService` instance directly as its own
pipeline step — see that use case's own module docstring. The same
"standalone entry point onto a shared service" shape
`app.modules.icd10_ai.application.use_cases.rank_icd10_suggestions
.RankICD10SuggestionsUseCase` establishes for itself.
"""

from app.modules.prescription_ai.application.dto import MedicationSafetyAnalysisInput
from app.modules.prescription_ai.application.services.medication_safety_analysis_service import (
    MedicationSafetyAnalysisService,
)
from app.modules.prescription_ai.domain.value_objects import MedicationSafetyFinding
from app.shared.application.use_case import UseCase


class AnalyzeMedicationSafetyUseCase(
    UseCase[MedicationSafetyAnalysisInput, tuple[MedicationSafetyFinding, ...]]
):
    def __init__(self, *, safety_service: MedicationSafetyAnalysisService) -> None:
        self._safety_service = safety_service

    async def execute(
        self, input_dto: MedicationSafetyAnalysisInput
    ) -> tuple[MedicationSafetyFinding, ...]:
        return self._safety_service.analyze(
            medications=input_dto.medications,
            existing_medications=input_dto.existing_medications,
            allergies=input_dto.allergies,
        )
