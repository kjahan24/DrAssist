"""Data Transfer Objects for the AI Prescription Assistance module's
application layer — use-case input/output shapes that aren't already a
domain value object in their own right."""

from dataclasses import dataclass, field

from app.modules.prescription_ai.domain.value_objects import (
    GenerationSession,
    MedicationSuggestion,
    PrescriptionSuggestionSet,
)


@dataclass(frozen=True, slots=True)
class GeneratedPrescriptionSuggestions:
    """`GeneratePrescriptionSuggestionUseCase`'s output — bundles the
    suggestion set (medications + merged safety findings) with its
    `GenerationSession`, the same "result + session" shape
    `app.modules.icd10_ai.application.dto.GeneratedICD10Suggestions`
    establishes for its own module."""

    suggestions: PrescriptionSuggestionSet
    session: GenerationSession


@dataclass(frozen=True, slots=True)
class PrescriptionContextValidationResultDTO:
    """`ValidatePrescriptionContextUseCase`'s output — deliberately non-
    throwing, the same "advisory pre-flight, distinct from constructor-
    level validation" shape
    `app.modules.icd10_ai.application.dto.ClinicalContextValidationResultDTO`
    establishes for its own module."""

    is_valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class MedicationSafetyAnalysisInput:
    """`AnalyzeMedicationSafetyUseCase`'s input — a medication list plus
    the clinical context the deterministic checks need (existing
    medications, allergies). Deliberately independent of
    `PrescriptionContextInput` so this use case is callable standalone
    against any assembled medication list, not only one this module just
    generated — the same "standalone entry point onto a shared service"
    shape `app.modules.icd10_ai.application.use_cases
    .rank_icd10_suggestions.RankICD10SuggestionsUseCase` establishes for
    itself."""

    medications: tuple[MedicationSuggestion, ...]
    existing_medications: tuple[str, ...] = field(default_factory=tuple)
    allergies: tuple[str, ...] = field(default_factory=tuple)
