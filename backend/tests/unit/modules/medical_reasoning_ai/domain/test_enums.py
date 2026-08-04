"""Unit tests for the AI Medical Reasoning Engine's domain enums."""

from app.modules.medical_reasoning_ai.domain.enums import (
    EvidencePolarity,
    MedicalReasoningOutputFormat,
    PatientSex,
    PregnancyStatus,
    ReasoningSetting,
    ReasoningStatus,
    RedFlagPriority,
)


class TestReasoningSetting:
    def test_has_exactly_five_members(self) -> None:
        assert {member.value for member in ReasoningSetting} == {
            "outpatient",
            "inpatient",
            "emergency",
            "pediatric",
            "geriatric",
        }

    def test_is_constructible_from_its_string_value(self) -> None:
        assert ReasoningSetting("emergency") is ReasoningSetting.EMERGENCY


class TestMedicalReasoningOutputFormat:
    def test_has_exactly_three_members(self) -> None:
        assert {member.value for member in MedicalReasoningOutputFormat} == {
            "json",
            "markdown",
            "text",
        }


class TestEvidencePolarity:
    def test_has_exactly_two_members(self) -> None:
        assert {member.value for member in EvidencePolarity} == {"supporting", "contradicting"}


class TestRedFlagPriority:
    def test_has_exactly_four_members(self) -> None:
        assert {member.value for member in RedFlagPriority} == {
            "low",
            "moderate",
            "high",
            "critical",
        }


class TestReasoningStatus:
    def test_has_exactly_two_members(self) -> None:
        assert {member.value for member in ReasoningStatus} == {"completed", "failed"}


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
