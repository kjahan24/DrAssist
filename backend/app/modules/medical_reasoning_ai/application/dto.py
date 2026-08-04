"""Data Transfer Objects for the AI Medical Reasoning Engine's
application layer — use-case input/output shapes that aren't already a
domain value object in their own right."""

from dataclasses import dataclass

from app.modules.medical_reasoning_ai.domain.value_objects import (
    GenerationSession,
    MedicalReasoningResult,
)


@dataclass(frozen=True, slots=True)
class GeneratedMedicalReasoning:
    """`GenerateClinicalReasoningUseCase`'s output — bundles the enriched
    reasoning result with its `GenerationSession`, the same "result +
    session" shape
    `app.modules.differential_diagnosis_ai.application.dto
    .GeneratedDifferentialDiagnosis` establishes for its own module."""

    result: MedicalReasoningResult
    session: GenerationSession
