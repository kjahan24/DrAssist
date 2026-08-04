"""Unit tests for the AI Clinical Note Generation module's application
DTOs."""

from app.modules.clinical_note_ai.application.dto import (
    GeneratedClinicalNote,
    RenderClinicalNoteInput,
    ValidationResultDTO,
)
from app.modules.clinical_note_ai.domain.enums import ClinicalNoteOutputFormat
from tests.unit.modules.clinical_note_ai.application.fakes import (
    make_clinical_note,
    make_generation_session,
)


class TestGeneratedClinicalNote:
    def test_bundles_note_and_session(self) -> None:
        note = make_clinical_note()
        session = make_generation_session()

        result = GeneratedClinicalNote(note=note, session=session)

        assert result.note is note
        assert result.session is session


class TestRenderClinicalNoteInput:
    def test_bundles_note_and_target_format(self) -> None:
        note = make_clinical_note()

        result = RenderClinicalNoteInput(note=note, target_format=ClinicalNoteOutputFormat.TEXT)

        assert result.note is note
        assert result.target_format is ClinicalNoteOutputFormat.TEXT


class TestValidationResultDTO:
    def test_defaults_errors_and_warnings_to_empty(self) -> None:
        result = ValidationResultDTO(is_valid=True)
        assert result.errors == ()
        assert result.warnings == ()

    def test_accepts_errors_and_warnings(self) -> None:
        result = ValidationResultDTO(is_valid=False, errors=("bad",), warnings=("meh",))
        assert result.is_valid is False
        assert result.errors == ("bad",)
        assert result.warnings == ("meh",)
