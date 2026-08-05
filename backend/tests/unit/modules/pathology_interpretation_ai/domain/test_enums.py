"""Unit tests for the AI Pathology Interpretation module's domain enums."""

from app.modules.pathology_interpretation_ai.domain.enums import (
    PathologyExaminationType,
    PathologyFindingCategory,
    PathologyInterpretationStatus,
    PathologyOutputFormat,
    PathologySetting,
    PatientSex,
    PregnancyStatus,
)


class TestPathologyExaminationType:
    def test_has_ten_examination_types(self) -> None:
        assert len(list(PathologyExaminationType)) == 10

    def test_includes_every_named_examination_type(self) -> None:
        values = {member.value for member in PathologyExaminationType}
        assert values == {
            "histopathology",
            "cytopathology",
            "fnac",
            "biopsy",
            "surgical_pathology",
            "hematopathology",
            "bone_marrow",
            "microbiology_culture",
            "molecular_pathology",
            "immunohistochemistry",
        }


class TestPathologySetting:
    def test_has_the_five_settings_this_tasks_prompts_section_names_in_order(self) -> None:
        assert list(PathologySetting) == [
            PathologySetting.OUTPATIENT,
            PathologySetting.INPATIENT,
            PathologySetting.EMERGENCY,
            PathologySetting.ONCOLOGY,
            PathologySetting.PEDIATRIC,
        ]

    def test_replaces_geriatric_with_oncology(self) -> None:
        values = {member.value for member in PathologySetting}
        assert "oncology" in values
        assert "geriatric" not in values


class TestPathologyOutputFormat:
    def test_has_json_markdown_and_text(self) -> None:
        assert {member.value for member in PathologyOutputFormat} == {
            "json",
            "markdown",
            "text",
        }


class TestPathologyFindingCategory:
    def test_has_the_three_categories(self) -> None:
        assert {member.value for member in PathologyFindingCategory} == {
            "benign",
            "malignant",
            "atypical",
        }


class TestPathologyInterpretationStatus:
    def test_has_completed_and_failed(self) -> None:
        assert {member.value for member in PathologyInterpretationStatus} == {
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
