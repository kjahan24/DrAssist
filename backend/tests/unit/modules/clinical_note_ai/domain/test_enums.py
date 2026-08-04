"""Unit tests for the AI Clinical Note Generation module's domain enums."""

from app.modules.clinical_note_ai.domain.enums import (
    ClinicalNoteOutputFormat,
    ClinicalNoteSectionName,
    GenerationStatus,
    NoteStyle,
)


class TestNoteStyle:
    def test_has_exactly_five_members(self) -> None:
        assert {member.value for member in NoteStyle} == {
            "concise",
            "detailed",
            "emergency",
            "outpatient",
            "follow_up",
        }

    def test_is_constructible_from_its_string_value(self) -> None:
        assert NoteStyle("concise") is NoteStyle.CONCISE


class TestClinicalNoteOutputFormat:
    def test_has_exactly_three_members(self) -> None:
        assert {member.value for member in ClinicalNoteOutputFormat} == {
            "json",
            "markdown",
            "text",
        }

    def test_is_constructible_from_its_string_value(self) -> None:
        assert ClinicalNoteOutputFormat("markdown") is ClinicalNoteOutputFormat.MARKDOWN


class TestClinicalNoteSectionName:
    def test_has_exactly_six_canonical_sections(self) -> None:
        assert {member.value for member in ClinicalNoteSectionName} == {
            "chief_complaint",
            "history_of_present_illness",
            "review_of_systems",
            "physical_examination",
            "assessment",
            "plan",
        }


class TestGenerationStatus:
    def test_has_exactly_two_members(self) -> None:
        assert {member.value for member in GenerationStatus} == {"completed", "failed"}
