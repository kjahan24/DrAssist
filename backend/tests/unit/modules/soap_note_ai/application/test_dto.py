"""Unit tests for the AI SOAP Note Generation module's application DTOs."""

from app.modules.soap_note_ai.application.dto import (
    GeneratedSOAPNote,
    RenderSOAPNoteInput,
    SOAPValidationResultDTO,
)
from app.modules.soap_note_ai.domain.enums import SOAPNoteOutputFormat
from tests.unit.modules.soap_note_ai.application.fakes import (
    make_generation_session,
    make_soap_note,
)


class TestGeneratedSOAPNote:
    def test_bundles_note_and_session(self) -> None:
        note = make_soap_note()
        session = make_generation_session()

        result = GeneratedSOAPNote(note=note, session=session)

        assert result.note is note
        assert result.session is session


class TestRenderSOAPNoteInput:
    def test_bundles_note_and_target_format(self) -> None:
        note = make_soap_note()

        result = RenderSOAPNoteInput(note=note, target_format=SOAPNoteOutputFormat.TEXT)

        assert result.note is note
        assert result.target_format is SOAPNoteOutputFormat.TEXT


class TestSOAPValidationResultDTO:
    def test_defaults_errors_and_warnings_to_empty(self) -> None:
        result = SOAPValidationResultDTO(is_valid=True)
        assert result.errors == ()
        assert result.warnings == ()

    def test_accepts_errors_and_warnings(self) -> None:
        result = SOAPValidationResultDTO(is_valid=False, errors=("bad",), warnings=("meh",))
        assert result.is_valid is False
        assert result.errors == ("bad",)
        assert result.warnings == ("meh",)
