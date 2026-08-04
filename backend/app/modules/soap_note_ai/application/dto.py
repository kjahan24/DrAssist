"""Data Transfer Objects for the AI SOAP Note Generation module's
application layer — use-case input/output shapes that aren't already a
domain value object in their own right."""

from dataclasses import dataclass, field

from app.modules.soap_note_ai.domain.enums import SOAPNoteOutputFormat
from app.modules.soap_note_ai.domain.value_objects import GenerationSession, SOAPNote


@dataclass(frozen=True, slots=True)
class GeneratedSOAPNote:
    """`GenerateSOAPNoteUseCase`'s output — bundles the note with its
    `GenerationSession`, the same "result + session" shape
    `app.modules.clinical_note_ai.application.dto.GeneratedClinicalNote`
    establishes for its own module."""

    note: SOAPNote
    session: GenerationSession


@dataclass(frozen=True, slots=True)
class RenderSOAPNoteInput:
    note: SOAPNote
    target_format: SOAPNoteOutputFormat


@dataclass(frozen=True, slots=True)
class SOAPValidationResultDTO:
    """`ValidateSOAPInputUseCase`'s output — deliberately non-throwing,
    the same "advisory pre-flight, distinct from constructor-level
    validation" shape
    `app.modules.clinical_note_ai.application.dto.ValidationResultDTO`
    establishes for its own module."""

    is_valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
