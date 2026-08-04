"""Unit tests for the AI Lab Interpretation module's domain enums."""

from app.modules.lab_interpretation_ai.domain.enums import (
    LabFindingFlag,
    LabInterpretationOutputFormat,
    LabInterpretationSetting,
    LabInterpretationStatus,
    PatientSex,
    PregnancyStatus,
)


class TestLabInterpretationSetting:
    def test_has_the_five_settings_this_tasks_prompts_section_names_in_order(self) -> None:
        assert list(LabInterpretationSetting) == [
            LabInterpretationSetting.OUTPATIENT,
            LabInterpretationSetting.INPATIENT,
            LabInterpretationSetting.EMERGENCY,
            LabInterpretationSetting.PEDIATRIC,
            LabInterpretationSetting.GERIATRIC,
        ]

    def test_values_are_lowercase_strings(self) -> None:
        assert LabInterpretationSetting.OUTPATIENT.value == "outpatient"
        assert LabInterpretationSetting.GERIATRIC.value == "geriatric"


class TestLabInterpretationOutputFormat:
    def test_has_json_markdown_and_text(self) -> None:
        assert {member.value for member in LabInterpretationOutputFormat} == {
            "json",
            "markdown",
            "text",
        }


class TestLabFindingFlag:
    def test_has_the_five_flags(self) -> None:
        assert {member.value for member in LabFindingFlag} == {
            "normal",
            "abnormal_low",
            "abnormal_high",
            "critical_low",
            "critical_high",
        }


class TestLabInterpretationStatus:
    def test_has_completed_and_failed(self) -> None:
        assert {member.value for member in LabInterpretationStatus} == {"completed", "failed"}


class TestPatientSex:
    def test_has_four_members(self) -> None:
        assert {member.value for member in PatientSex} == {
            "male",
            "female",
            "other",
            "unspecified",
        }


class TestPregnancyStatus:
    def test_has_four_members(self) -> None:
        assert {member.value for member in PregnancyStatus} == {
            "not_pregnant",
            "pregnant",
            "unknown",
            "not_applicable",
        }
