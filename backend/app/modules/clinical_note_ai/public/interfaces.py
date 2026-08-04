"""The AI Clinical Note Generation module's public port — the only
contract another module may depend on
(`docs/backend-architecture/03_module_architecture.md`,
`10_module_communication.md`).

Never import from `app.modules.clinical_note_ai.domain`, `.application`
(beyond this package's own re-exports in `public/dto.py`), or
`.infrastructure` from outside this module. A future clinical-note-owning
module (the real, persisted "Clinical Note" feature, once built) is the
expected consumer: it calls `generate_note` to get an AI-drafted note,
lets its own workflow route the result to a clinician for review/edit,
and only then persists it — this module itself never saves anything,
per this task's own "It DOES NOT save notes. It ONLY generates AI
output" scope.

`stream_generate_note` bypasses `GenerateClinicalNoteUseCase`'s parse/
validate/audit pipeline — see `infrastructure/generation
/clinical_note_generator.py`'s own module docstring for why.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.modules.clinical_note_ai.public.dto import (
    ClinicalEncounterInput,
    ClinicalNote,
    ClinicalNoteOutputFormat,
    ClinicalNoteStreamChunk,
    GeneratedClinicalNote,
    ValidationResultDTO,
)


class ClinicalNoteAIPort(ABC):
    @abstractmethod
    async def generate_note(self, encounter: ClinicalEncounterInput) -> GeneratedClinicalNote: ...

    @abstractmethod
    def stream_generate_note(
        self, encounter: ClinicalEncounterInput
    ) -> AsyncIterator[ClinicalNoteStreamChunk]: ...

    @abstractmethod
    async def render_note(
        self, note: ClinicalNote, *, target_format: ClinicalNoteOutputFormat
    ) -> str: ...

    @abstractmethod
    async def validate_input(self, encounter: ClinicalEncounterInput) -> ValidationResultDTO: ...
