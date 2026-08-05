"""Unit tests for the AI Radiology Interpretation module's domain enums."""

from app.modules.radiology_interpretation_ai.domain.enums import (
    PatientSex,
    PregnancyStatus,
    RadiologyExaminationType,
    RadiologyFindingCategory,
    RadiologyInterpretationStatus,
    RadiologyOutputFormat,
    RadiologySetting,
)


class TestRadiologyExaminationType:
    def test_has_thirteen_examination_types(self) -> None:
        assert len(list(RadiologyExaminationType)) == 13

    def test_includes_every_named_modality(self) -> None:
        values = {member.value for member in RadiologyExaminationType}
        assert values == {
            "chest_xray",
            "abdomen_xray",
            "ct_brain",
            "ct_chest",
            "ct_abdomen",
            "ct_pelvis",
            "mri_brain",
            "mri_spine",
            "mri_knee",
            "ultrasound",
            "echocardiography",
            "mammography",
            "general",
        }


class TestRadiologySetting:
    def test_has_the_five_settings_this_tasks_prompts_section_names_in_order(self) -> None:
        assert list(RadiologySetting) == [
            RadiologySetting.OUTPATIENT,
            RadiologySetting.INPATIENT,
            RadiologySetting.EMERGENCY,
            RadiologySetting.PEDIATRIC,
            RadiologySetting.GERIATRIC,
        ]


class TestRadiologyOutputFormat:
    def test_has_json_markdown_and_text(self) -> None:
        assert {member.value for member in RadiologyOutputFormat} == {
            "json",
            "markdown",
            "text",
        }


class TestRadiologyFindingCategory:
    def test_has_the_four_categories(self) -> None:
        assert {member.value for member in RadiologyFindingCategory} == {
            "normal",
            "abnormal",
            "incidental",
            "critical",
        }


class TestRadiologyInterpretationStatus:
    def test_has_completed_and_failed(self) -> None:
        assert {member.value for member in RadiologyInterpretationStatus} == {
            "completed",
            "failed",
        }


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
