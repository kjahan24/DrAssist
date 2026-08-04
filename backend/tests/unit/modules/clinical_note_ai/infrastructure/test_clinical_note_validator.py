"""Unit tests for `DefaultClinicalNoteValidator`."""

import pytest

from app.modules.clinical_note_ai.domain.exceptions import (
    EmptyAIResponseError,
    HallucinatedPlaceholderError,
    MissingClinicalNoteSectionError,
)
from app.modules.clinical_note_ai.domain.value_objects import ClinicalNote, ClinicalNoteSection
from app.modules.clinical_note_ai.infrastructure.validation.clinical_note_validator import (
    DefaultClinicalNoteValidator,
)
from tests.unit.modules.clinical_note_ai.application.fakes import make_clinical_note


class TestValidateHappyPath:
    def test_accepts_a_fully_populated_note(self) -> None:
        validator = DefaultClinicalNoteValidator()
        validator.validate(make_clinical_note())


class TestValidateEmptyResponse:
    def test_raises_when_every_canonical_section_is_blank(self) -> None:
        validator = DefaultClinicalNoteValidator()
        note = ClinicalNote(
            sections=tuple(
                ClinicalNoteSection(name=name, content="")
                for name in (
                    "chief_complaint",
                    "history_of_present_illness",
                    "review_of_systems",
                    "physical_examination",
                    "assessment",
                    "plan",
                )
            ),
            raw_text="{}",
            output_format=make_clinical_note().output_format,
        )

        with pytest.raises(EmptyAIResponseError):
            validator.validate(note)


class TestValidateMissingSections:
    def test_raises_when_one_canonical_section_is_blank(self) -> None:
        validator = DefaultClinicalNoteValidator()
        note = make_clinical_note(
            sections=(
                ClinicalNoteSection(name="chief_complaint", content="Headache"),
                ClinicalNoteSection(name="history_of_present_illness", content="Gradual onset"),
                ClinicalNoteSection(name="review_of_systems", content="Negative"),
                ClinicalNoteSection(name="physical_examination", content="Unremarkable"),
                ClinicalNoteSection(name="assessment", content="Tension headache"),
                ClinicalNoteSection(name="plan", content=""),
            )
        )

        with pytest.raises(MissingClinicalNoteSectionError) as exc_info:
            validator.validate(note)
        assert exc_info.value.section_name == "plan"

    def test_raises_when_a_canonical_section_is_whitespace_only(self) -> None:
        validator = DefaultClinicalNoteValidator()
        note = make_clinical_note(
            sections=(
                ClinicalNoteSection(name="chief_complaint", content="Headache"),
                ClinicalNoteSection(name="history_of_present_illness", content="Gradual onset"),
                ClinicalNoteSection(name="review_of_systems", content="Negative"),
                ClinicalNoteSection(name="physical_examination", content="Unremarkable"),
                ClinicalNoteSection(name="assessment", content="   "),
                ClinicalNoteSection(name="plan", content="OTC analgesics"),
            )
        )

        with pytest.raises(MissingClinicalNoteSectionError) as exc_info:
            validator.validate(note)
        assert exc_info.value.section_name == "assessment"


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
        validator = DefaultClinicalNoteValidator()
        note = make_clinical_note(
            sections=(
                ClinicalNoteSection(name="chief_complaint", content="Headache"),
                ClinicalNoteSection(
                    name="history_of_present_illness", content=f"Patient reports {placeholder}."
                ),
                ClinicalNoteSection(name="review_of_systems", content="Negative"),
                ClinicalNoteSection(name="physical_examination", content="Unremarkable"),
                ClinicalNoteSection(name="assessment", content="Tension headache"),
                ClinicalNoteSection(name="plan", content="OTC analgesics"),
            )
        )

        with pytest.raises(HallucinatedPlaceholderError) as exc_info:
            validator.validate(note)
        assert exc_info.value.section_name == "history_of_present_illness"

    def test_does_not_flag_ordinary_clinical_language(self) -> None:
        validator = DefaultClinicalNoteValidator()
        # Sanity check: legitimate clinical text (which may contain
        # capitalized words like acronyms) must never be flagged.
        validator.validate(make_clinical_note())
