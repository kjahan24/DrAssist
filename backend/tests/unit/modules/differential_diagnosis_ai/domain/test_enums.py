"""Unit tests for the AI Differential Diagnosis module's domain enums."""

from app.modules.differential_diagnosis_ai.domain.enums import (
    ClinicalSetting,
    DifferentialOutputFormat,
    GenerationStatus,
    PatientSex,
    PregnancyStatus,
    UrgencyLevel,
)


class TestClinicalSetting:
    def test_has_exactly_five_members(self) -> None:
        assert {member.value for member in ClinicalSetting} == {
            "outpatient",
            "emergency",
            "inpatient",
            "pediatric",
            "geriatric",
        }

    def test_is_constructible_from_its_string_value(self) -> None:
        assert ClinicalSetting("pediatric") is ClinicalSetting.PEDIATRIC


class TestDifferentialOutputFormat:
    def test_has_exactly_three_members(self) -> None:
        assert {member.value for member in DifferentialOutputFormat} == {
            "json",
            "markdown",
            "text",
        }


class TestUrgencyLevel:
    def test_has_exactly_three_members(self) -> None:
        assert {member.value for member in UrgencyLevel} == {"routine", "urgent", "emergent"}


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


class TestPregnancyStatus:
    def test_has_exactly_four_members(self) -> None:
        assert {member.value for member in PregnancyStatus} == {
            "not_pregnant",
            "pregnant",
            "unknown",
            "not_applicable",
        }
