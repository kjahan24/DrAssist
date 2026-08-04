"""Data Transfer Objects for the AI Differential Diagnosis module's
application layer — use-case input/output shapes that aren't already a
domain value object in their own right."""

from dataclasses import dataclass, field

from app.modules.differential_diagnosis_ai.domain.value_objects import (
    DifferentialDiagnosisResult,
    GenerationSession,
)


@dataclass(frozen=True, slots=True)
class GeneratedDifferentialDiagnosis:
    """`GenerateDifferentialDiagnosisUseCase`'s output — bundles the
    ranked result with its `GenerationSession`, the same "result +
    session" shape
    `app.modules.prescription_ai.application.dto
    .GeneratedPrescriptionSuggestions` establishes for its own module."""

    result: DifferentialDiagnosisResult
    session: GenerationSession


@dataclass(frozen=True, slots=True)
class ClinicalEvidenceValidationResultDTO:
    """`ValidateClinicalEvidenceUseCase`'s output — deliberately non-
    throwing, the same "advisory pre-flight, distinct from constructor-
    level validation" shape
    `app.modules.prescription_ai.application.dto
    .PrescriptionContextValidationResultDTO` establishes for its own
    module."""

    is_valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
