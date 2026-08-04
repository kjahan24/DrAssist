"""Public DTOs — the only data shapes another module may depend on.

Re-exported from the domain/application layers, not redefined, the same
"exactly one definition of each shape" precedent
`app.modules.soap_note_ai.public.dto` establishes for its own module.
"""

from app.modules.icd10_ai.application.dto import (
    ClinicalContextValidationResultDTO,
    GeneratedICD10Suggestions,
)
from app.modules.icd10_ai.domain.enums import (
    CodingSetting,
    DiagnosisFlag,
    ICD10OutputFormat,
    PatientSex,
)
from app.modules.icd10_ai.domain.value_objects import (
    GenerationSession,
    ICD10CodingInput,
    ICD10StreamChunk,
    ICD10Suggestion,
    ICD10SuggestionSet,
)

__all__ = [
    "ClinicalContextValidationResultDTO",
    "CodingSetting",
    "DiagnosisFlag",
    "GeneratedICD10Suggestions",
    "GenerationSession",
    "ICD10CodingInput",
    "ICD10OutputFormat",
    "ICD10StreamChunk",
    "ICD10Suggestion",
    "ICD10SuggestionSet",
    "PatientSex",
]
