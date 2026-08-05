"""Tests for the AI Risk Stratification & Early Warning Score module's
domain enums — membership, values, and the string-enum contract."""

import pytest

from app.modules.risk_stratification_ai.domain.enums import (
    ConsciousnessLevel,
    OverallRiskLevel,
    RiskAnalysisStatus,
    RiskCategory,
    RiskStratificationOutputFormat,
    RiskStratificationSetting,
)


class TestRiskStratificationSetting:
    def test_has_exactly_six_members(self) -> None:
        assert len(RiskStratificationSetting) == 6

    @pytest.mark.parametrize(
        ("member", "value"),
        [
            (RiskStratificationSetting.EMERGENCY, "emergency"),
            (RiskStratificationSetting.INPATIENT, "inpatient"),
            (RiskStratificationSetting.ICU, "icu"),
            (RiskStratificationSetting.OUTPATIENT, "outpatient"),
            (RiskStratificationSetting.PEDIATRIC, "pediatric"),
            (RiskStratificationSetting.GERIATRIC, "geriatric"),
        ],
    )
    def test_member_values(self, member: RiskStratificationSetting, value: str) -> None:
        assert member.value == value

    def test_is_str_subclass(self) -> None:
        assert isinstance(RiskStratificationSetting.OUTPATIENT, str)


class TestRiskStratificationOutputFormat:
    def test_has_exactly_three_members(self) -> None:
        assert len(RiskStratificationOutputFormat) == 3

    @pytest.mark.parametrize(
        ("member", "value"),
        [
            (RiskStratificationOutputFormat.JSON, "json"),
            (RiskStratificationOutputFormat.MARKDOWN, "markdown"),
            (RiskStratificationOutputFormat.TEXT, "text"),
        ],
    )
    def test_member_values(self, member: RiskStratificationOutputFormat, value: str) -> None:
        assert member.value == value


class TestRiskCategory:
    def test_has_exactly_fourteen_members(self) -> None:
        assert len(RiskCategory) == 14

    @pytest.mark.parametrize(
        ("member", "value"),
        [
            (RiskCategory.NEWS2, "news2"),
            (RiskCategory.MEWS, "mews"),
            (RiskCategory.QSOFA, "qsofa"),
            (RiskCategory.SOFA_SIMPLIFIED, "sofa_simplified"),
            (RiskCategory.SEPSIS_RISK, "sepsis_risk"),
            (RiskCategory.AKI_RISK, "aki_risk"),
            (RiskCategory.RESPIRATORY_DETERIORATION, "respiratory_deterioration"),
            (RiskCategory.CARDIOVASCULAR_RISK, "cardiovascular_risk"),
            (RiskCategory.STROKE_RISK, "stroke_risk"),
            (RiskCategory.BLEEDING_RISK, "bleeding_risk"),
            (RiskCategory.FALL_RISK, "fall_risk"),
            (RiskCategory.READMISSION_RISK, "readmission_risk"),
            (RiskCategory.MORTALITY_RISK, "mortality_risk"),
            (RiskCategory.GENERAL_CLINICAL_DETERIORATION, "general_clinical_deterioration"),
        ],
    )
    def test_member_values(self, member: RiskCategory, value: str) -> None:
        assert member.value == value

    def test_standardized_categories_are_first_four(self) -> None:
        members = list(RiskCategory)
        assert members[:4] == [
            RiskCategory.NEWS2,
            RiskCategory.MEWS,
            RiskCategory.QSOFA,
            RiskCategory.SOFA_SIMPLIFIED,
        ]


class TestOverallRiskLevel:
    def test_has_exactly_four_members(self) -> None:
        assert len(OverallRiskLevel) == 4

    @pytest.mark.parametrize(
        ("member", "value"),
        [
            (OverallRiskLevel.LOW, "low"),
            (OverallRiskLevel.MODERATE, "moderate"),
            (OverallRiskLevel.HIGH, "high"),
            (OverallRiskLevel.CRITICAL, "critical"),
        ],
    )
    def test_member_values(self, member: OverallRiskLevel, value: str) -> None:
        assert member.value == value


class TestConsciousnessLevel:
    def test_has_exactly_four_members(self) -> None:
        assert len(ConsciousnessLevel) == 4

    @pytest.mark.parametrize(
        ("member", "value"),
        [
            (ConsciousnessLevel.ALERT, "alert"),
            (ConsciousnessLevel.VOICE, "voice"),
            (ConsciousnessLevel.PAIN, "pain"),
            (ConsciousnessLevel.UNRESPONSIVE, "unresponsive"),
        ],
    )
    def test_member_values(self, member: ConsciousnessLevel, value: str) -> None:
        assert member.value == value


class TestRiskAnalysisStatus:
    def test_has_exactly_two_members(self) -> None:
        assert len(RiskAnalysisStatus) == 2

    @pytest.mark.parametrize(
        ("member", "value"),
        [
            (RiskAnalysisStatus.COMPLETED, "completed"),
            (RiskAnalysisStatus.FAILED, "failed"),
        ],
    )
    def test_member_values(self, member: RiskAnalysisStatus, value: str) -> None:
        assert member.value == value
