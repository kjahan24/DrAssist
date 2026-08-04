"""Unit tests for the AI ICD-10 Coding module's domain enums."""

from app.modules.icd10_ai.domain.enums import (
    CodingSetting,
    DiagnosisFlag,
    GenerationStatus,
    ICD10OutputFormat,
    PatientSex,
)


class TestCodingSetting:
    def test_has_exactly_four_members(self) -> None:
        assert {member.value for member in CodingSetting} == {
            "outpatient",
            "emergency",
            "inpatient",
            "follow_up",
        }

    def test_is_constructible_from_its_string_value(self) -> None:
        assert CodingSetting("outpatient") is CodingSetting.OUTPATIENT


class TestICD10OutputFormat:
    def test_has_exactly_three_members(self) -> None:
        assert {member.value for member in ICD10OutputFormat} == {"json", "markdown", "text"}


class TestDiagnosisFlag:
    def test_has_exactly_two_members(self) -> None:
        assert {member.value for member in DiagnosisFlag} == {"primary", "secondary"}


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
