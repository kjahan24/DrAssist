"""The AI SOAP Note Generation module's public port — the only contract
another module may depend on
(`docs/backend-architecture/03_module_architecture.md`,
`10_module_communication.md`).

Never import from `app.modules.soap_note_ai.domain`, `.application`
(beyond this package's own re-exports in `public/dto.py`), or
`.infrastructure` from outside this module. A future SOAP-note-owning
module (the real, persisted "SOAP Note" feature — `app.modules.soap_notes`
already exists for structured SOAP data, but has no AI drafting of its
own yet) is the expected consumer: it calls `generate_note` to get an
AI-drafted SOAP note, lets its own workflow route the result to a
clinician for review/edit, and only then persists it — this module
itself never saves anything, per this task's own "It ONLY generates AI
output. It DOES NOT save notes" scope.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.modules.soap_note_ai.public.dto import (
    GeneratedSOAPNote,
    SOAPEncounterInput,
    SOAPNote,
    SOAPNoteOutputFormat,
    SOAPNoteStreamChunk,
    SOAPValidationResultDTO,
)


class SOAPNoteAIPort(ABC):
    @abstractmethod
    async def generate_note(self, encounter: SOAPEncounterInput) -> GeneratedSOAPNote: ...

    @abstractmethod
    def stream_generate_note(
        self, encounter: SOAPEncounterInput
    ) -> AsyncIterator[SOAPNoteStreamChunk]: ...

    @abstractmethod
    async def render_note(self, note: SOAPNote, *, target_format: SOAPNoteOutputFormat) -> str: ...

    @abstractmethod
    async def validate_input(self, encounter: SOAPEncounterInput) -> SOAPValidationResultDTO: ...
