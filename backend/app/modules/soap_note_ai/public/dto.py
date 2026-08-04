"""Public DTOs — the only data shapes another module may depend on.

Re-exported from the domain/application layers, not redefined, the same
"exactly one definition of each shape" precedent
`app.modules.clinical_note_ai.public.dto` establishes for its own module.
"""

from app.modules.soap_note_ai.application.dto import (
    GeneratedSOAPNote,
    RenderSOAPNoteInput,
    SOAPValidationResultDTO,
)
from app.modules.soap_note_ai.domain.enums import PatientSex, SOAPNoteOutputFormat, SOAPStyle
from app.modules.soap_note_ai.domain.value_objects import (
    GenerationSession,
    SOAPEncounterInput,
    SOAPNote,
    SOAPNoteStreamChunk,
    SOAPSection,
)

__all__ = [
    "GeneratedSOAPNote",
    "GenerationSession",
    "PatientSex",
    "RenderSOAPNoteInput",
    "SOAPEncounterInput",
    "SOAPNote",
    "SOAPNoteOutputFormat",
    "SOAPNoteStreamChunk",
    "SOAPSection",
    "SOAPStyle",
    "SOAPValidationResultDTO",
]
