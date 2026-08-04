"""Public DTOs — the only data shapes another module may depend on.

Re-exported from the domain/application layers, not redefined, the same
"exactly one definition of each shape" precedent
`app.modules.icd10_ai.public.dto` establishes for its own module.
"""

from app.modules.prescription_ai.application.dto import (
    GeneratedPrescriptionSuggestions,
    MedicationSafetyAnalysisInput,
    PrescriptionContextValidationResultDTO,
)
from app.modules.prescription_ai.domain.enums import (
    AdministrationRoute,
    PatientSex,
    PregnancyStatus,
    PrescribingSetting,
    PrescriptionOutputFormat,
    SafetyFindingCategory,
    SafetySeverity,
)
from app.modules.prescription_ai.domain.value_objects import (
    GenerationSession,
    MedicationSafetyFinding,
    MedicationSuggestion,
    PrescriptionContextInput,
    PrescriptionStreamChunk,
    PrescriptionSuggestionSet,
)

__all__ = [
    "AdministrationRoute",
    "GeneratedPrescriptionSuggestions",
    "GenerationSession",
    "MedicationSafetyAnalysisInput",
    "MedicationSafetyFinding",
    "MedicationSuggestion",
    "PatientSex",
    "PregnancyStatus",
    "PrescribingSetting",
    "PrescriptionContextInput",
    "PrescriptionContextValidationResultDTO",
    "PrescriptionOutputFormat",
    "PrescriptionStreamChunk",
    "PrescriptionSuggestionSet",
    "SafetyFindingCategory",
    "SafetySeverity",
]
