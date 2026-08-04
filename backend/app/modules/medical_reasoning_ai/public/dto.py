"""Public DTOs — the only data shapes another module may depend on.

Re-exported from the domain/application layers, not redefined, the same
"exactly one definition of each shape" precedent
`app.modules.differential_diagnosis_ai.public.dto` establishes for its
own module.
"""

from app.modules.medical_reasoning_ai.application.dto import GeneratedMedicalReasoning
from app.modules.medical_reasoning_ai.domain.enums import (
    EvidencePolarity,
    MedicalReasoningOutputFormat,
    PatientSex,
    PregnancyStatus,
    ReasoningSetting,
    RedFlagPriority,
)
from app.modules.medical_reasoning_ai.domain.value_objects import (
    EvidenceItem,
    GenerationSession,
    MedicalReasoningInput,
    MedicalReasoningResult,
    MedicalReasoningStreamChunk,
    RedFlag,
)

__all__ = [
    "EvidenceItem",
    "EvidencePolarity",
    "GeneratedMedicalReasoning",
    "GenerationSession",
    "MedicalReasoningInput",
    "MedicalReasoningOutputFormat",
    "MedicalReasoningResult",
    "MedicalReasoningStreamChunk",
    "PatientSex",
    "PregnancyStatus",
    "ReasoningSetting",
    "RedFlag",
    "RedFlagPriority",
]
