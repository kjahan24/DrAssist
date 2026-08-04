"""`RenderSOAPNoteUseCase` — re-renders an already-generated `SOAPNote`
into any of the three output formats without a second AI call, per
`application/services/soap_note_renderer.py`'s own docstring on why
rendering is independent of generation."""

from app.modules.soap_note_ai.application.dto import RenderSOAPNoteInput
from app.modules.soap_note_ai.application.services.soap_note_renderer import SOAPNoteRenderer
from app.shared.application.use_case import UseCase


class RenderSOAPNoteUseCase(UseCase[RenderSOAPNoteInput, str]):
    def __init__(self, *, renderer: SOAPNoteRenderer) -> None:
        self._renderer = renderer

    async def execute(self, input_dto: RenderSOAPNoteInput) -> str:
        return self._renderer.render(input_dto.note, input_dto.target_format)
