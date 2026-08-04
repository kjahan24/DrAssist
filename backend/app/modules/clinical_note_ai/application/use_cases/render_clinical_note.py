"""`RenderClinicalNoteUseCase` — re-renders an already-generated
`ClinicalNote` into any of the three output formats without a second AI
call, per `application/services/clinical_note_renderer.py`'s own
docstring on why rendering is independent of generation."""

from app.modules.clinical_note_ai.application.dto import RenderClinicalNoteInput
from app.modules.clinical_note_ai.application.services.clinical_note_renderer import (
    ClinicalNoteRenderer,
)
from app.shared.application.use_case import UseCase


class RenderClinicalNoteUseCase(UseCase[RenderClinicalNoteInput, str]):
    def __init__(self, *, renderer: ClinicalNoteRenderer) -> None:
        self._renderer = renderer

    async def execute(self, input_dto: RenderClinicalNoteInput) -> str:
        return self._renderer.render(input_dto.note, input_dto.target_format)
