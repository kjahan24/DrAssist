"""Tests for `RiskExplanationService`."""

from app.modules.risk_stratification_ai.application.services.risk_explanation_service import (
    RiskExplanationService,
)
from app.modules.risk_stratification_ai.domain.enums import RiskCategory
from tests.unit.modules.risk_stratification_ai.application.fakes import make_risk_score


class TestMergeRiskScores:
    def test_returns_ai_scores_unchanged_when_no_deterministic_scores(self) -> None:
        service = RiskExplanationService()
        ai_score = make_risk_score(category=RiskCategory.NEWS2)

        result = service.merge_risk_scores((ai_score,), ())

        assert result == (ai_score,)

    def test_returns_deterministic_scores_when_no_ai_scores(self) -> None:
        service = RiskExplanationService()
        det_score = make_risk_score(category=RiskCategory.MEWS)

        result = service.merge_risk_scores((), (det_score,))

        assert result == (det_score,)

    def test_deterministic_score_value_wins_for_same_category(self) -> None:
        service = RiskExplanationService()
        ai_score = make_risk_score(category=RiskCategory.NEWS2, score_value=1.0)
        det_score = make_risk_score(category=RiskCategory.NEWS2, score_value=7.0)

        result = service.merge_risk_scores((ai_score,), (det_score,))

        assert len(result) == 1
        assert result[0].score_value == 7.0

    def test_contributing_factors_are_combined_and_deduplicated(self) -> None:
        service = RiskExplanationService()
        ai_score = make_risk_score(
            category=RiskCategory.NEWS2, contributing_factors=("Tachycardia", "Fever")
        )
        det_score = make_risk_score(
            category=RiskCategory.NEWS2, contributing_factors=("Fever", "Hypoxia")
        )

        result = service.merge_risk_scores((ai_score,), (det_score,))

        assert result[0].contributing_factors == ("Tachycardia", "Fever", "Hypoxia")

    def test_prefers_ai_clinical_explanation_when_present(self) -> None:
        service = RiskExplanationService()
        ai_score = make_risk_score(
            category=RiskCategory.NEWS2, clinical_explanation="AI narrative explanation."
        )
        det_score = make_risk_score(
            category=RiskCategory.NEWS2, clinical_explanation="Deterministic explanation."
        )

        result = service.merge_risk_scores((ai_score,), (det_score,))

        assert result[0].clinical_explanation == "AI narrative explanation."

    def test_falls_back_to_deterministic_explanation_when_ai_explanation_blank(self) -> None:
        service = RiskExplanationService()
        ai_score = make_risk_score(category=RiskCategory.NEWS2, clinical_explanation="   ")
        det_score = make_risk_score(
            category=RiskCategory.NEWS2, clinical_explanation="Deterministic explanation."
        )

        result = service.merge_risk_scores((ai_score,), (det_score,))

        assert result[0].clinical_explanation == "Deterministic explanation."

    def test_different_categories_produce_separate_entries(self) -> None:
        service = RiskExplanationService()
        ai_score = make_risk_score(category=RiskCategory.NEWS2)
        det_score = make_risk_score(category=RiskCategory.QSOFA)

        result = service.merge_risk_scores((ai_score,), (det_score,))

        assert len(result) == 2
        assert {score.category for score in result} == {RiskCategory.NEWS2, RiskCategory.QSOFA}

    def test_both_empty_returns_empty(self) -> None:
        service = RiskExplanationService()
        assert service.merge_risk_scores((), ()) == ()


class TestBuildClinicalReasoning:
    def test_returns_ai_reasoning_when_non_blank(self) -> None:
        service = RiskExplanationService()
        result = service.build_clinical_reasoning("AI-authored reasoning.", ())
        assert result == "AI-authored reasoning."

    def test_synthesizes_from_risk_scores_when_ai_reasoning_blank(self) -> None:
        service = RiskExplanationService()
        score = make_risk_score(clinical_explanation="NEWS2 score of 7.")

        result = service.build_clinical_reasoning("", (score,))

        assert result == "NEWS2 score of 7."

    def test_combines_multiple_risk_score_explanations(self) -> None:
        service = RiskExplanationService()
        scores = (
            make_risk_score(category=RiskCategory.NEWS2, clinical_explanation="NEWS2 score of 7."),
            make_risk_score(category=RiskCategory.QSOFA, clinical_explanation="qSOFA score of 2."),
        )

        result = service.build_clinical_reasoning("", scores)

        assert result == "NEWS2 score of 7. qSOFA score of 2."

    def test_returns_empty_string_when_nothing_to_synthesize(self) -> None:
        service = RiskExplanationService()
        assert service.build_clinical_reasoning("", ()) == ""

    def test_skips_blank_explanations_when_synthesizing(self) -> None:
        service = RiskExplanationService()
        scores = (
            make_risk_score(category=RiskCategory.NEWS2, clinical_explanation="   "),
            make_risk_score(category=RiskCategory.QSOFA, clinical_explanation="qSOFA score of 2."),
        )

        result = service.build_clinical_reasoning("", scores)

        assert result == "qSOFA score of 2."
