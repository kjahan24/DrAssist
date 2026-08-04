"""Public DTOs — the only data shapes another module may depend on.

Re-exported from the domain/application layers, not redefined, the same
"exactly one definition of each shape" precedent
`app.modules.ai_copilot.public.dto` and `app.modules.ai.public.dto` both
establish for their own modules.
"""

from app.modules.clinical_note_ai.application.dto import (
    GeneratedClinicalNote,
    RenderClinicalNoteInput,
    ValidationResultDTO,
)
from app.modules.clinical_note_ai.domain.enums import ClinicalNoteOutputFormat, NoteStyle
from app.modules.clinical_note_ai.domain.value_objects import (
    ClinicalEncounterInput,
    ClinicalNote,
    ClinicalNoteSection,
    ClinicalNoteStreamChunk,
    GenerationSession,
)

__all__ = [
    "ClinicalEncounterInput",
    "ClinicalNote",
    "ClinicalNoteOutputFormat",
    "ClinicalNoteSection",
    "ClinicalNoteStreamChunk",
    "GeneratedClinicalNote",
    "GenerationSession",
    "NoteStyle",
    "RenderClinicalNoteInput",
    "ValidationResultDTO",
]
