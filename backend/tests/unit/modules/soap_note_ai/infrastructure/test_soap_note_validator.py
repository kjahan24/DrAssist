"""Unit tests for `DefaultSOAPNoteValidator`."""

import pytest

from app.modules.soap_note_ai.domain.exceptions import (
    DuplicatedSOAPSectionError,
    EmptySOAPResponseError,
    HallucinatedPlaceholderError,
    InvalidMarkdownFormatError,
    MissingSOAPSectionError,
)
from app.modules.soap_note_ai.domain.value_objects import SOAPNote, SOAPSection
from app.modules.soap_note_ai.infrastructure.validation.soap_note_validator import (
    DefaultSOAPNoteValidator,
)
from tests.unit.modules.soap_note_ai.application.fakes import make_soap_note


class TestValidateHappyPath:
    def test_accepts_a_fully_populated_note(self) -> None:
        validator = DefaultSOAPNoteValidator()
        validator.validate(make_soap_note())


class TestValidateEmptyResponse:
    def test_raises_when_every_canonical_section_is_blank(self) -> None:
        validator = DefaultSOAPNoteValidator()
        note = SOAPNote(
            sections=tuple(
                SOAPSection(name=name, content="")
                for name in ("subjective", "objective", "assessment", "plan")
            ),
            raw_text="{}",
            output_format=make_soap_note().output_format,
        )

        with pytest.raises(EmptySOAPResponseError):
            validator.validate(note)


class TestValidateMissingSections:
    def test_raises_when_one_canonical_section_is_blank(self) -> None:
        validator = DefaultSOAPNoteValidator()
        note = make_soap_note(
            sections=(
                SOAPSection(name="subjective", content="Reports headache"),
                SOAPSection(name="objective", content="BP 120/80"),
                SOAPSection(name="assessment", content="Tension headache"),
                SOAPSection(name="plan", content=""),
            )
        )

        with pytest.raises(MissingSOAPSectionError) as exc_info:
            validator.validate(note)
        assert exc_info.value.section_name == "plan"

    def test_raises_when_a_canonical_section_is_whitespace_only(self) -> None:
        validator = DefaultSOAPNoteValidator()
        note = make_soap_note(
            sections=(
                SOAPSection(name="subjective", content="Reports headache"),
                SOAPSection(name="objective", content="BP 120/80"),
                SOAPSection(name="assessment", content="   "),
                SOAPSection(name="plan", content="OTC analgesics"),
            )
        )

        with pytest.raises(MissingSOAPSectionError) as exc_info:
            validator.validate(note)
        assert exc_info.value.section_name == "assessment"


class TestValidateDuplicatedSections:
    def test_raises_when_two_sections_share_identical_content(self) -> None:
        validator = DefaultSOAPNoteValidator()
        note = make_soap_note(
            sections=(
                SOAPSection(name="subjective", content="Reports headache since yesterday."),
                SOAPSection(name="objective", content="Reports headache since yesterday."),
                SOAPSection(name="assessment", content="Tension headache"),
                SOAPSection(name="plan", content="OTC analgesics"),
            )
        )

        with pytest.raises(DuplicatedSOAPSectionError) as exc_info:
            validator.validate(note)
        assert exc_info.value.first_section == "subjective"
        assert exc_info.value.second_section == "objective"

    def test_duplicate_detection_is_case_and_whitespace_insensitive(self) -> None:
        validator = DefaultSOAPNoteValidator()
        note = make_soap_note(
            sections=(
                SOAPSection(name="subjective", content="Tension headache"),
                SOAPSection(name="objective", content="BP 120/80"),
                SOAPSection(name="assessment", content="  TENSION HEADACHE  "),
                SOAPSection(name="plan", content="OTC analgesics"),
            )
        )

        with pytest.raises(DuplicatedSOAPSectionError):
            validator.validate(note)

    def test_does_not_flag_genuinely_different_sections(self) -> None:
        validator = DefaultSOAPNoteValidator()
        validator.validate(make_soap_note())


class TestValidateHallucinatedPlaceholders:
    @pytest.mark.parametrize(
        "placeholder",
        [
            "[insert history here]",
            "[PLACEHOLDER]",
            "<insert findings>",
            "TBD",
            "TODO",
            "XXX",
            "Lorem ipsum dolor sit amet",
            "[Patient Name]",
        ],
    )
    def test_raises_when_a_section_contains_a_placeholder(self, placeholder: str) -> None:
        validator = DefaultSOAPNoteValidator()
        note = make_soap_note(
            sections=(
                SOAPSection(name="subjective", content=f"Patient reports {placeholder}."),
                SOAPSection(name="objective", content="BP 120/80"),
                SOAPSection(name="assessment", content="Tension headache"),
                SOAPSection(name="plan", content="OTC analgesics"),
            )
        )

        with pytest.raises(HallucinatedPlaceholderError) as exc_info:
            validator.validate(note)
        assert exc_info.value.section_name == "subjective"

    def test_does_not_flag_ordinary_clinical_language(self) -> None:
        validator = DefaultSOAPNoteValidator()
        # Sanity check: legitimate clinical text (which may contain
        # capitalized words like acronyms) must never be flagged.
        validator.validate(make_soap_note())


class TestValidateInvalidMarkdown:
    def test_raises_on_unbalanced_code_fence(self) -> None:
        validator = DefaultSOAPNoteValidator()
        note = make_soap_note(
            sections=(
                SOAPSection(name="subjective", content="Reports headache"),
                SOAPSection(name="objective", content="BP 120/80"),
                SOAPSection(name="assessment", content="Tension headache ``` broken"),
                SOAPSection(name="plan", content="OTC analgesics"),
            )
        )

        with pytest.raises(InvalidMarkdownFormatError) as exc_info:
            validator.validate(note)
        assert exc_info.value.section_name == "assessment"

    def test_raises_on_unbalanced_bold_marker(self) -> None:
        validator = DefaultSOAPNoteValidator()
        note = make_soap_note(
            sections=(
                SOAPSection(name="subjective", content="Reports **severe headache"),
                SOAPSection(name="objective", content="BP 120/80"),
                SOAPSection(name="assessment", content="Tension headache"),
                SOAPSection(name="plan", content="OTC analgesics"),
            )
        )

        with pytest.raises(InvalidMarkdownFormatError) as exc_info:
            validator.validate(note)
        assert exc_info.value.section_name == "subjective"

    def test_balanced_markers_do_not_raise(self) -> None:
        validator = DefaultSOAPNoteValidator()
        note = make_soap_note(
            sections=(
                SOAPSection(name="subjective", content="Reports **severe** headache"),
                SOAPSection(name="objective", content="BP 120/80, see ```note``` above"),
                SOAPSection(name="assessment", content="Tension headache"),
                SOAPSection(name="plan", content="OTC analgesics"),
            )
        )

        validator.validate(note)
