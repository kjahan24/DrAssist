"""Public DTOs — the only data shapes another module may depend on.

Re-exported from the domain/application layers, not redefined, the same
"exactly one definition of each shape" precedent every prior AI module's
own `public/dto.py` establishes for itself.
"""

from app.modules.patient_education_ai.application.dto import GeneratedPatientEducation
from app.modules.patient_education_ai.domain.enums import (
    EducationGenerationStatus,
    PatientEducationOutputFormat,
    PatientEducationSetting,
)
from app.modules.patient_education_ai.domain.value_objects import (
    GenerationSession,
    PatientEducationInput,
    PatientEducationResult,
    PatientEducationStreamChunk,
)

__all__ = [
    "EducationGenerationStatus",
    "GeneratedPatientEducation",
    "GenerationSession",
    "PatientEducationInput",
    "PatientEducationOutputFormat",
    "PatientEducationResult",
    "PatientEducationSetting",
    "PatientEducationStreamChunk",
]
