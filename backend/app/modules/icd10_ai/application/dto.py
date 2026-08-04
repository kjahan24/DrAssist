"""Data Transfer Objects for the AI ICD-10 Coding module's application
layer — use-case input/output shapes that aren't already a domain value
object in their own right."""

from dataclasses import dataclass, field

from app.modules.icd10_ai.domain.value_objects import GenerationSession, ICD10SuggestionSet


@dataclass(frozen=True, slots=True)
class GeneratedICD10Suggestions:
    """`GenerateICD10SuggestionsUseCase`'s output — bundles the ranked
    suggestion set with its `GenerationSession`, the same "result +
    session" shape
    `app.modules.soap_note_ai.application.dto.GeneratedSOAPNote`
    establishes for its own module."""

    suggestions: ICD10SuggestionSet
    session: GenerationSession


@dataclass(frozen=True, slots=True)
class ClinicalContextValidationResultDTO:
    """`ValidateClinicalContextUseCase`'s output — deliberately non-
    throwing, the same "advisory pre-flight, distinct from constructor-
    level validation" shape
    `app.modules.soap_note_ai.application.dto.SOAPValidationResultDTO`
    establishes for its own module."""

    is_valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
