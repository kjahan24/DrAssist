"""Tests for the AI Patient Education & Discharge Instructions module's
domain enums — membership, values, and the string-enum contract."""

import pytest

from app.modules.patient_education_ai.domain.enums import (
    EducationGenerationStatus,
    PatientEducationOutputFormat,
    PatientEducationSetting,
)


class TestPatientEducationSetting:
    def test_has_exactly_six_members(self) -> None:
        assert len(PatientEducationSetting) == 6

    @pytest.mark.parametrize(
        ("member", "value"),
        [
            (PatientEducationSetting.ADULT, "adult"),
            (PatientEducationSetting.PEDIATRIC, "pediatric"),
            (PatientEducationSetting.GERIATRIC, "geriatric"),
            (PatientEducationSetting.PREGNANCY, "pregnancy"),
            (PatientEducationSetting.EMERGENCY_DISCHARGE, "emergency_discharge"),
            (PatientEducationSetting.HOSPITAL_DISCHARGE, "hospital_discharge"),
        ],
    )
    def test_member_values(self, member: PatientEducationSetting, value: str) -> None:
        assert member.value == value

    def test_is_str_subclass(self) -> None:
        assert isinstance(PatientEducationSetting.ADULT, str)


class TestPatientEducationOutputFormat:
    def test_has_exactly_three_members(self) -> None:
        assert len(PatientEducationOutputFormat) == 3

    @pytest.mark.parametrize(
        ("member", "value"),
        [
            (PatientEducationOutputFormat.JSON, "json"),
            (PatientEducationOutputFormat.MARKDOWN, "markdown"),
            (PatientEducationOutputFormat.TEXT, "text"),
        ],
    )
    def test_member_values(self, member: PatientEducationOutputFormat, value: str) -> None:
        assert member.value == value


class TestEducationGenerationStatus:
    def test_has_exactly_two_members(self) -> None:
        assert len(EducationGenerationStatus) == 2

    @pytest.mark.parametrize(
        ("member", "value"),
        [
            (EducationGenerationStatus.COMPLETED, "completed"),
            (EducationGenerationStatus.FAILED, "failed"),
        ],
    )
    def test_member_values(self, member: EducationGenerationStatus, value: str) -> None:
        assert member.value == value
