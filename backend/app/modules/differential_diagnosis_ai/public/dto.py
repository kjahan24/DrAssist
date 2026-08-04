"""Public DTOs — the only data shapes another module may depend on.

Re-exported from the domain/application layers, not redefined, the same
"exactly one definition of each shape" precedent
`app.modules.prescription_ai.public.dto` establishes for its own module.
"""

from app.modules.differential_diagnosis_ai.application.dto import (
    ClinicalEvidenceValidationResultDTO,
    GeneratedDifferentialDiagnosis,
)
from app.modules.differential_diagnosis_ai.domain.enums import (
    ClinicalSetting,
    DifferentialOutputFormat,
    PatientSex,
    PregnancyStatus,
    UrgencyLevel,
)
from app.modules.differential_diagnosis_ai.domain.value_objects import (
    DifferentialDiagnosisCandidate,
    DifferentialDiagnosisInput,
    DifferentialDiagnosisResult,
    DifferentialDiagnosisStreamChunk,
    GenerationSession,
)

__all__ = [
    "ClinicalEvidenceValidationResultDTO",
    "ClinicalSetting",
    "DifferentialDiagnosisCandidate",
    "DifferentialDiagnosisInput",
    "DifferentialDiagnosisResult",
    "DifferentialDiagnosisStreamChunk",
    "DifferentialOutputFormat",
    "GeneratedDifferentialDiagnosis",
    "GenerationSession",
    "PatientSex",
    "PregnancyStatus",
    "UrgencyLevel",
]
