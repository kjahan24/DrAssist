"""Unit tests confirming `public/dto.py` re-exports the correct shapes
without redefining them."""

from app.modules.clinical_note_ai.application.dto import (
    GeneratedClinicalNote as ApplicationGeneratedClinicalNote,
)
from app.modules.clinical_note_ai.domain.enums import ClinicalNoteOutputFormat as DomainFormat
from app.modules.clinical_note_ai.domain.enums import NoteStyle as DomainNoteStyle
from app.modules.clinical_note_ai.domain.value_objects import (
    ClinicalEncounterInput as DomainClinicalEncounterInput,
)
from app.modules.clinical_note_ai.domain.value_objects import ClinicalNote as DomainClinicalNote
from app.modules.clinical_note_ai.public.dto import (
    ClinicalEncounterInput,
    ClinicalNote,
    ClinicalNoteOutputFormat,
    GeneratedClinicalNote,
    NoteStyle,
)


class TestPublicDtoReExports:
    def test_clinical_encounter_input_is_the_domain_type(self) -> None:
        assert ClinicalEncounterInput is DomainClinicalEncounterInput

    def test_clinical_note_is_the_domain_type(self) -> None:
        assert ClinicalNote is DomainClinicalNote

    def test_generated_clinical_note_is_the_application_type(self) -> None:
        assert GeneratedClinicalNote is ApplicationGeneratedClinicalNote

    def test_note_style_is_the_domain_type(self) -> None:
        assert NoteStyle is DomainNoteStyle

    def test_clinical_note_output_format_is_the_domain_type(self) -> None:
        assert ClinicalNoteOutputFormat is DomainFormat
