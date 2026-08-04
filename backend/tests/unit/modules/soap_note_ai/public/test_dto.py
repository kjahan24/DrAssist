"""Unit tests confirming `public/dto.py` re-exports the correct shapes
without redefining them."""

from app.modules.soap_note_ai.application.dto import (
    GeneratedSOAPNote as ApplicationGeneratedSOAPNote,
)
from app.modules.soap_note_ai.domain.enums import PatientSex as DomainPatientSex
from app.modules.soap_note_ai.domain.enums import SOAPNoteOutputFormat as DomainFormat
from app.modules.soap_note_ai.domain.enums import SOAPStyle as DomainSOAPStyle
from app.modules.soap_note_ai.domain.value_objects import (
    SOAPEncounterInput as DomainSOAPEncounterInput,
)
from app.modules.soap_note_ai.domain.value_objects import SOAPNote as DomainSOAPNote
from app.modules.soap_note_ai.public.dto import (
    GeneratedSOAPNote,
    PatientSex,
    SOAPEncounterInput,
    SOAPNote,
    SOAPNoteOutputFormat,
    SOAPStyle,
)


class TestPublicDtoReExports:
    def test_soap_encounter_input_is_the_domain_type(self) -> None:
        assert SOAPEncounterInput is DomainSOAPEncounterInput

    def test_soap_note_is_the_domain_type(self) -> None:
        assert SOAPNote is DomainSOAPNote

    def test_generated_soap_note_is_the_application_type(self) -> None:
        assert GeneratedSOAPNote is ApplicationGeneratedSOAPNote

    def test_soap_style_is_the_domain_type(self) -> None:
        assert SOAPStyle is DomainSOAPStyle

    def test_soap_note_output_format_is_the_domain_type(self) -> None:
        assert SOAPNoteOutputFormat is DomainFormat

    def test_patient_sex_is_the_domain_type(self) -> None:
        assert PatientSex is DomainPatientSex
