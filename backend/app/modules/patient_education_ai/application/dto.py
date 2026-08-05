"""Data Transfer Objects for the AI Patient Education & Discharge
Instructions module's application layer — use-case input/output shapes
that aren't already a domain value object in their own right."""

from dataclasses import dataclass

from app.modules.patient_education_ai.domain.value_objects import (
    GenerationSession,
    PatientEducationResult,
)


@dataclass(frozen=True, slots=True)
class GeneratedPatientEducation:
    """`GeneratePatientEducationUseCase`'s output — bundles the enriched
    result with its `GenerationSession`, the same "result + session"
    shape every prior AI module's own use-case DTO establishes for
    itself."""

    result: PatientEducationResult
    session: GenerationSession
