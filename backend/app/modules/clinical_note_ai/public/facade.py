"""`ClinicalNoteAIFacade` — the one concrete implementation of
`ClinicalNoteAIPort`. Constructed by
`app.modules.clinical_note_ai.container.get_clinical_note_ai_facade`.
"""

from collections.abc import AsyncIterator

from app.modules.clinical_note_ai.application.dto import (
    GeneratedClinicalNote,
    RenderClinicalNoteInput,
    ValidationResultDTO,
)
from app.modules.clinical_note_ai.application.ports import ClinicalNoteGeneratorPort
from app.modules.clinical_note_ai.application.use_cases.generate_clinical_note import (
    GenerateClinicalNoteUseCase,
)
from app.modules.clinical_note_ai.application.use_cases.render_clinical_note import (
    RenderClinicalNoteUseCase,
)
from app.modules.clinical_note_ai.application.use_cases.validate_clinical_input import (
    ValidateClinicalInputUseCase,
)
from app.modules.clinical_note_ai.public.dto import (
    ClinicalEncounterInput,
    ClinicalNote,
    ClinicalNoteOutputFormat,
    ClinicalNoteStreamChunk,
)
from app.modules.clinical_note_ai.public.interfaces import ClinicalNoteAIPort


class ClinicalNoteAIFacade(ClinicalNoteAIPort):
    def __init__(
        self,
        *,
        generate_use_case: GenerateClinicalNoteUseCase,
        validate_use_case: ValidateClinicalInputUseCase,
        render_use_case: RenderClinicalNoteUseCase,
        generator: ClinicalNoteGeneratorPort,
    ) -> None:
        self._generate_use_case = generate_use_case
        self._validate_use_case = validate_use_case
        self._render_use_case = render_use_case
        self._generator = generator

    async def generate_note(self, encounter: ClinicalEncounterInput) -> GeneratedClinicalNote:
        return await self._generate_use_case.execute(encounter)

    def stream_generate_note(
        self, encounter: ClinicalEncounterInput
    ) -> AsyncIterator[ClinicalNoteStreamChunk]:
        return self._generator.stream_generate(encounter)

    async def render_note(
        self, note: ClinicalNote, *, target_format: ClinicalNoteOutputFormat
    ) -> str:
        return await self._render_use_case.execute(
            RenderClinicalNoteInput(note=note, target_format=target_format)
        )

    async def validate_input(self, encounter: ClinicalEncounterInput) -> ValidationResultDTO:
        return await self._validate_use_case.execute(encounter)
