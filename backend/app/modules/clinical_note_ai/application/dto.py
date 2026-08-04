"""Data Transfer Objects for the AI Clinical Note Generation module's
application layer — use-case input/output shapes that aren't already a
domain value object in their own right."""

from dataclasses import dataclass, field

from app.modules.clinical_note_ai.domain.enums import ClinicalNoteOutputFormat
from app.modules.clinical_note_ai.domain.value_objects import ClinicalNote, GenerationSession


@dataclass(frozen=True, slots=True)
class GeneratedClinicalNote:
    """`GenerateClinicalNoteUseCase`'s output — bundles the note with its
    `GenerationSession`, the same "result + session" shape
    `app.modules.ai_copilot.application.dto.AIResponse` establishes for
    its own module, so a caller gets provider/latency/token/cost
    information alongside the generated content without a second call."""

    note: ClinicalNote
    session: GenerationSession


@dataclass(frozen=True, slots=True)
class RenderClinicalNoteInput:
    note: ClinicalNote
    target_format: ClinicalNoteOutputFormat


@dataclass(frozen=True, slots=True)
class ValidationResultDTO:
    """`ValidateClinicalInputUseCase`'s output — deliberately non-throwing
    (unlike `ClinicalEncounterInput.__post_init__`'s Tier 3 structural
    validation, which raises) so a caller can offer a "check before you
    generate" pre-flight without wrapping every call in a `try/except`."""

    is_valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
