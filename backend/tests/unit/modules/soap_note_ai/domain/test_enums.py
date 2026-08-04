"""Unit tests for the AI SOAP Note Generation module's domain enums."""

from app.modules.soap_note_ai.domain.enums import (
    GenerationStatus,
    PatientSex,
    SOAPNoteOutputFormat,
    SOAPSectionName,
    SOAPStyle,
)


class TestSOAPStyle:
    def test_has_exactly_five_members(self) -> None:
        assert {member.value for member in SOAPStyle} == {
            "concise",
            "standard",
            "detailed",
            "emergency",
            "follow_up",
        }

    def test_is_constructible_from_its_string_value(self) -> None:
        assert SOAPStyle("standard") is SOAPStyle.STANDARD


class TestSOAPNoteOutputFormat:
    def test_has_exactly_three_members(self) -> None:
        assert {member.value for member in SOAPNoteOutputFormat} == {"json", "markdown", "text"}


class TestSOAPSectionName:
    def test_has_exactly_four_canonical_sections(self) -> None:
        assert {member.value for member in SOAPSectionName} == {
            "subjective",
            "objective",
            "assessment",
            "plan",
        }


class TestGenerationStatus:
    def test_has_exactly_two_members(self) -> None:
        assert {member.value for member in GenerationStatus} == {"completed", "failed"}


class TestPatientSex:
    def test_has_exactly_four_members(self) -> None:
        assert {member.value for member in PatientSex} == {
            "male",
            "female",
            "other",
            "unspecified",
        }
