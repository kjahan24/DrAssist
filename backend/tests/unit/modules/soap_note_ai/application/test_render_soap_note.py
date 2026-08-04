"""Unit tests for `RenderSOAPNoteUseCase`."""

from app.modules.soap_note_ai.application.dto import RenderSOAPNoteInput
from app.modules.soap_note_ai.application.services.soap_note_renderer import SOAPNoteRenderer
from app.modules.soap_note_ai.application.use_cases.render_soap_note import RenderSOAPNoteUseCase
from app.modules.soap_note_ai.domain.enums import SOAPNoteOutputFormat
from tests.unit.modules.soap_note_ai.application.fakes import make_soap_note


class TestRenderSOAPNoteUseCase:
    async def test_delegates_to_the_renderer_for_json(self) -> None:
        use_case = RenderSOAPNoteUseCase(renderer=SOAPNoteRenderer())
        note = make_soap_note()

        result = await use_case.execute(
            RenderSOAPNoteInput(note=note, target_format=SOAPNoteOutputFormat.JSON)
        )

        assert "subjective" in result

    async def test_delegates_to_the_renderer_for_markdown(self) -> None:
        use_case = RenderSOAPNoteUseCase(renderer=SOAPNoteRenderer())
        note = make_soap_note()

        result = await use_case.execute(
            RenderSOAPNoteInput(note=note, target_format=SOAPNoteOutputFormat.MARKDOWN)
        )

        assert "## Subjective" in result

    async def test_delegates_to_the_renderer_for_text(self) -> None:
        use_case = RenderSOAPNoteUseCase(renderer=SOAPNoteRenderer())
        note = make_soap_note()

        result = await use_case.execute(
            RenderSOAPNoteInput(note=note, target_format=SOAPNoteOutputFormat.TEXT)
        )

        assert "SUBJECTIVE:" in result
