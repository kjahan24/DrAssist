"""Tests for `MonitoringRecommendationService`."""

import pytest

from app.modules.risk_stratification_ai.application.services.monitoring_recommendation_service import (  # noqa: E501
    MonitoringRecommendationService,
)
from app.modules.risk_stratification_ai.domain.enums import RiskCategory
from tests.unit.modules.risk_stratification_ai.application.fakes import (
    FakeEarlyWarningPort,
    make_risk_score,
)

_ALL_CATEGORIES = tuple(RiskCategory)


class TestRecommendMonitoring:
    @pytest.mark.parametrize("category", _ALL_CATEGORIES)
    def test_every_category_has_a_monitoring_recommendation(self, category: RiskCategory) -> None:
        service = MonitoringRecommendationService(early_warning_port=FakeEarlyWarningPort())
        score = make_risk_score(category=category)

        result = service.recommend_monitoring((score,))

        assert len(result) == 1
        assert result[0]

    def test_empty_scores_produces_empty_recommendations(self) -> None:
        service = MonitoringRecommendationService(early_warning_port=FakeEarlyWarningPort())
        assert service.recommend_monitoring(()) == ()

    def test_duplicate_categories_are_deduplicated(self) -> None:
        service = MonitoringRecommendationService(early_warning_port=FakeEarlyWarningPort())
        scores = (
            make_risk_score(category=RiskCategory.NEWS2),
            make_risk_score(category=RiskCategory.NEWS2, score_value=5.0),
        )

        result = service.recommend_monitoring(scores)

        assert len(result) == 1


class TestSuggestFollowUp:
    @pytest.mark.parametrize("category", _ALL_CATEGORIES)
    def test_every_category_has_a_follow_up_recommendation(self, category: RiskCategory) -> None:
        service = MonitoringRecommendationService(early_warning_port=FakeEarlyWarningPort())
        score = make_risk_score(category=category)

        result = service.suggest_follow_up((score,))

        assert len(result) == 1
        assert result[0]

    def test_empty_scores_produces_empty_follow_up(self) -> None:
        service = MonitoringRecommendationService(early_warning_port=FakeEarlyWarningPort())
        assert service.suggest_follow_up(()) == ()


class TestSuggestEscalation:
    def test_delegates_to_early_warning_port(self) -> None:
        score = make_risk_score(category=RiskCategory.NEWS2)
        port = FakeEarlyWarningPort(escalation_by_category={RiskCategory.NEWS2: "Urgent review."})
        service = MonitoringRecommendationService(early_warning_port=port)

        result = service.suggest_escalation((score,))

        assert result == ("Urgent review.",)
        assert port.escalation_calls == [score]

    def test_skips_none_escalations(self) -> None:
        score = make_risk_score(category=RiskCategory.NEWS2)
        service = MonitoringRecommendationService(early_warning_port=FakeEarlyWarningPort())

        result = service.suggest_escalation((score,))

        assert result == ()

    def test_deduplicates_identical_escalation_text(self) -> None:
        scores = (
            make_risk_score(category=RiskCategory.NEWS2),
            make_risk_score(category=RiskCategory.MEWS),
        )
        port = FakeEarlyWarningPort(
            escalation_by_category={
                RiskCategory.NEWS2: "Urgent review.",
                RiskCategory.MEWS: "Urgent review.",
            }
        )
        service = MonitoringRecommendationService(early_warning_port=port)

        result = service.suggest_escalation(scores)

        assert result == ("Urgent review.",)

    def test_empty_scores_produces_empty_escalation(self) -> None:
        service = MonitoringRecommendationService(early_warning_port=FakeEarlyWarningPort())
        assert service.suggest_escalation(()) == ()
