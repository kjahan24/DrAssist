"""Unit tests for `StaticClinicalRiskKnowledgeBase` — per this task's
own explicit "Sepsis risk tests" TESTS requirement, extended to cover
every one of the ten curated `RiskCategory` members this port owns."""

import pytest

from app.modules.risk_stratification_ai.domain.enums import RiskCategory
from app.modules.risk_stratification_ai.domain.value_objects import LabValue, RiskScore
from app.modules.risk_stratification_ai.infrastructure.clinical_risk.static_clinical_risk_knowledge_base import (  # noqa: E501
    StaticClinicalRiskKnowledgeBase,
)
from tests.unit.modules.risk_stratification_ai.application.fakes import make_lab_value

_KB = StaticClinicalRiskKnowledgeBase()


def _identify(
    category: RiskCategory,
    *,
    diagnoses: tuple[str, ...] = (),
    medical_history: tuple[str, ...] = (),
    current_medications: tuple[str, ...] = (),
    lab_values: tuple[LabValue, ...] = (),
    patient_age: int | None = None,
) -> RiskScore | None:
    return _KB.identify_risk_factors(
        category,
        diagnoses=diagnoses,
        medical_history=medical_history,
        current_medications=current_medications,
        lab_values=lab_values,
        patient_age=patient_age,
    )


class TestStandardizedCategoriesAreNotCovered:
    @pytest.mark.parametrize(
        "category",
        [RiskCategory.NEWS2, RiskCategory.MEWS, RiskCategory.QSOFA, RiskCategory.SOFA_SIMPLIFIED],
    )
    def test_returns_none_for_standardized_categories(self, category: RiskCategory) -> None:
        assert _identify(category, diagnoses=("Sepsis",)) is None


class TestSepsisRisk:
    def test_matches_a_sepsis_diagnosis(self) -> None:
        score = _identify(RiskCategory.SEPSIS_RISK, diagnoses=("Sepsis",))
        assert score is not None
        assert score.category is RiskCategory.SEPSIS_RISK

    def test_matches_pneumonia_in_medical_history(self) -> None:
        score = _identify(RiskCategory.SEPSIS_RISK, medical_history=("Pneumonia last year",))
        assert score is not None

    def test_returns_none_when_no_keyword_matches(self) -> None:
        assert _identify(RiskCategory.SEPSIS_RISK, diagnoses=("Fractured wrist",)) is None

    def test_score_value_is_none(self) -> None:
        score = _identify(RiskCategory.SEPSIS_RISK, diagnoses=("Sepsis",))
        assert score is not None
        assert score.score_value is None


class TestAkiRisk:
    def test_matches_chronic_kidney_disease(self) -> None:
        score = _identify(RiskCategory.AKI_RISK, medical_history=("Chronic kidney disease",))
        assert score is not None

    def test_matches_nephrotoxic_medication(self) -> None:
        score = _identify(RiskCategory.AKI_RISK, current_medications=("Ibuprofen (NSAID)",))
        assert score is not None

    def test_matches_elevated_creatinine(self) -> None:
        score = _identify(RiskCategory.AKI_RISK, lab_values=(make_lab_value(numeric_value=2.0),))
        assert score is not None
        assert any("creatinine" in factor.lower() for factor in score.contributing_factors)

    def test_normal_creatinine_does_not_match(self) -> None:
        assert (
            _identify(RiskCategory.AKI_RISK, lab_values=(make_lab_value(numeric_value=0.8),))
            is None
        )

    def test_returns_none_when_no_keyword_matches(self) -> None:
        assert _identify(RiskCategory.AKI_RISK, diagnoses=("Fractured wrist",)) is None


class TestRespiratoryDeterioration:
    def test_matches_copd(self) -> None:
        assert _identify(RiskCategory.RESPIRATORY_DETERIORATION, diagnoses=("COPD",)) is not None

    def test_returns_none_when_no_keyword_matches(self) -> None:
        assert _identify(RiskCategory.RESPIRATORY_DETERIORATION, diagnoses=("Gout",)) is None


class TestCardiovascularRisk:
    def test_matches_heart_failure(self) -> None:
        assert _identify(RiskCategory.CARDIOVASCULAR_RISK, diagnoses=("Heart failure",)) is not None

    def test_returns_none_when_no_keyword_matches(self) -> None:
        assert _identify(RiskCategory.CARDIOVASCULAR_RISK, diagnoses=("Gout",)) is None


class TestStrokeRisk:
    def test_matches_atrial_fibrillation(self) -> None:
        assert _identify(RiskCategory.STROKE_RISK, diagnoses=("Atrial fibrillation",)) is not None

    def test_returns_none_when_no_keyword_matches(self) -> None:
        assert _identify(RiskCategory.STROKE_RISK, diagnoses=("Gout",)) is None


class TestBleedingRisk:
    def test_matches_warfarin_medication(self) -> None:
        assert _identify(RiskCategory.BLEEDING_RISK, current_medications=("Warfarin",)) is not None

    def test_matches_peptic_ulcer_history(self) -> None:
        assert (
            _identify(RiskCategory.BLEEDING_RISK, medical_history=("Peptic ulcer disease",))
            is not None
        )

    def test_returns_none_when_no_keyword_matches(self) -> None:
        assert _identify(RiskCategory.BLEEDING_RISK, current_medications=("Metformin",)) is None


class TestFallRisk:
    def test_matches_fall_history(self) -> None:
        assert _identify(RiskCategory.FALL_RISK, medical_history=("Fall last month",)) is not None

    def test_matches_sedative_medication(self) -> None:
        assert (
            _identify(RiskCategory.FALL_RISK, current_medications=("Lorazepam (benzodiazepine)",))
            is not None
        )

    def test_matches_age_over_threshold(self) -> None:
        assert _identify(RiskCategory.FALL_RISK, patient_age=80) is not None

    def test_age_under_threshold_does_not_match_alone(self) -> None:
        assert _identify(RiskCategory.FALL_RISK, patient_age=40) is None

    def test_returns_none_when_nothing_matches(self) -> None:
        assert _identify(RiskCategory.FALL_RISK) is None


class TestReadmissionRisk:
    def test_matches_heart_failure_history(self) -> None:
        assert (
            _identify(RiskCategory.READMISSION_RISK, medical_history=("Heart failure",)) is not None
        )

    def test_returns_none_when_no_keyword_matches(self) -> None:
        assert _identify(RiskCategory.READMISSION_RISK, diagnoses=("Gout",)) is None


class TestMortalityRisk:
    def test_matches_metastatic_cancer(self) -> None:
        assert _identify(RiskCategory.MORTALITY_RISK, diagnoses=("Metastatic cancer",)) is not None

    def test_returns_none_when_no_keyword_matches(self) -> None:
        assert _identify(RiskCategory.MORTALITY_RISK, diagnoses=("Gout",)) is None


class TestGeneralClinicalDeterioration:
    def test_matches_frailty(self) -> None:
        assert (
            _identify(RiskCategory.GENERAL_CLINICAL_DETERIORATION, medical_history=("Frailty",))
            is not None
        )

    def test_matches_age_over_threshold(self) -> None:
        assert _identify(RiskCategory.GENERAL_CLINICAL_DETERIORATION, patient_age=85) is not None

    def test_returns_none_when_nothing_matches(self) -> None:
        assert _identify(RiskCategory.GENERAL_CLINICAL_DETERIORATION, patient_age=50) is None
