"""Data Transfer Objects for the AI Lab Interpretation module's
application layer — use-case input/output shapes that aren't already a
domain value object in their own right."""

from dataclasses import dataclass

from app.modules.lab_interpretation_ai.domain.value_objects import (
    GenerationSession,
    LabInterpretationResult,
)


@dataclass(frozen=True, slots=True)
class GeneratedLabInterpretation:
    """`InterpretLabResultsUseCase`'s output — bundles the enriched
    interpretation result with its `GenerationSession`, the same
    "result + session" shape every prior AI module's own use-case DTO
    establishes for itself."""

    result: LabInterpretationResult
    session: GenerationSession
