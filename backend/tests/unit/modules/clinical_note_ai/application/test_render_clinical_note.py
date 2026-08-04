"""Unit tests for `RenderClinicalNoteUseCase`."""

from app.modules.clinical_note_ai.application.dto import RenderClinicalNoteInput
from app.modules.clinical_note_ai.application.services.clinical_note_renderer import (
    ClinicalNoteRenderer,
)
from app.modules.clinical_note_ai.application.use_cases.render_clinical_note import (
    RenderClinicalNoteUseCase,
)
from app.modules.clinical_note_ai.domain.enums import ClinicalNoteOutputFormat
from tests.unit.modules.clinical_note_ai.application.fakes import make_clinical_note


class TestRenderClinicalNoteUseCase:
    async def test_delegates_to_the_renderer(self) -> None:
        use_case = RenderClinicalNoteUseCase(renderer=ClinicalNoteRenderer())
        note = make_clinical_note()

        result = await use_case.execute(
            RenderClinicalNoteInput(note=note, target_format=ClinicalNoteOutputFormat.TEXT)
        )

        assert "CHIEF COMPLAINT:" in result

    async def test_can_render_the_same_note_in_multiple_formats(self) -> None:
        use_case = RenderClinicalNoteUseCase(renderer=ClinicalNoteRenderer())
        note = make_clinical_note()

        json_result = await use_case.execute(
            RenderClinicalNoteInput(note=note, target_format=ClinicalNoteOutputFormat.JSON)
        )
        markdown_result = await use_case.execute(
            RenderClinicalNoteInput(note=note, target_format=ClinicalNoteOutputFormat.MARKDOWN)
        )

        assert json_result != markdown_result
        assert json_result.startswith("{")
        assert markdown_result.startswith("##")
