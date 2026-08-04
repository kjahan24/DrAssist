"""`SOAPNoteAIFacade` — the one concrete implementation of
`SOAPNoteAIPort`. Constructed by
`app.modules.soap_note_ai.container.get_soap_note_ai_facade`.
"""

from collections.abc import AsyncIterator

from app.modules.soap_note_ai.application.dto import (
    GeneratedSOAPNote,
    RenderSOAPNoteInput,
    SOAPValidationResultDTO,
)
from app.modules.soap_note_ai.application.ports import SOAPGeneratorPort
from app.modules.soap_note_ai.application.use_cases.generate_soap_note import (
    GenerateSOAPNoteUseCase,
)
from app.modules.soap_note_ai.application.use_cases.render_soap_note import RenderSOAPNoteUseCase
from app.modules.soap_note_ai.application.use_cases.validate_soap_input import (
    ValidateSOAPInputUseCase,
)
from app.modules.soap_note_ai.public.dto import (
    SOAPEncounterInput,
    SOAPNote,
    SOAPNoteOutputFormat,
    SOAPNoteStreamChunk,
)
from app.modules.soap_note_ai.public.interfaces import SOAPNoteAIPort


class SOAPNoteAIFacade(SOAPNoteAIPort):
    def __init__(
        self,
        *,
        generate_use_case: GenerateSOAPNoteUseCase,
        validate_use_case: ValidateSOAPInputUseCase,
        render_use_case: RenderSOAPNoteUseCase,
        generator: SOAPGeneratorPort,
    ) -> None:
        self._generate_use_case = generate_use_case
        self._validate_use_case = validate_use_case
        self._render_use_case = render_use_case
        self._generator = generator

    async def generate_note(self, encounter: SOAPEncounterInput) -> GeneratedSOAPNote:
        return await self._generate_use_case.execute(encounter)

    def stream_generate_note(
        self, encounter: SOAPEncounterInput
    ) -> AsyncIterator[SOAPNoteStreamChunk]:
        return self._generator.stream_generate(encounter)

    async def render_note(self, note: SOAPNote, *, target_format: SOAPNoteOutputFormat) -> str:
        return await self._render_use_case.execute(
            RenderSOAPNoteInput(note=note, target_format=target_format)
        )

    async def validate_input(self, encounter: SOAPEncounterInput) -> SOAPValidationResultDTO:
        return await self._validate_use_case.execute(encounter)
