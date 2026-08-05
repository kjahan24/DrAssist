"""Tests for `RiskScoringService`."""

from app.modules.risk_stratification_ai.application.services.risk_scoring_service import (
    RiskScoringService,
)
from app.modules.risk_stratification_ai.domain.enums import RiskCategory
from tests.unit.modules.risk_stratification_ai.application.fakes import (
    FakeRiskScoringPort,
    make_risk_score,
    make_vital_signs,
)


class TestComputeStandardizedScores:
    def test_returns_empty_tuple_when_all_scores_are_none(self) -> None:
        service = RiskScoringService(scoring_port=FakeRiskScoringPort())
        result = service.compute_standardized_scores(make_vital_signs(), ())
        assert result == ()

    def test_returns_only_the_non_none_scores(self) -> None:
        news2 = make_risk_score(category=RiskCategory.NEWS2, score_value=3.0)
        qsofa = make_risk_score(category=RiskCategory.QSOFA, score_value=1.0)
        port = FakeRiskScoringPort(news2=news2, qsofa=qsofa)
        service = RiskScoringService(scoring_port=port)

        result = service.compute_standardized_scores(make_vital_signs(), ())

        assert result == (news2, qsofa)

    def test_calls_all_four_score_computations(self) -> None:
        port = FakeRiskScoringPort()
        service = RiskScoringService(scoring_port=port)

        service.compute_standardized_scores(make_vital_signs(), ())

        assert port.calls == ["news2", "mews", "qsofa", "sofa_simplified"]

    def test_returns_all_four_when_all_present(self) -> None:
        scores = {
            "news2": make_risk_score(category=RiskCategory.NEWS2),
            "mews": make_risk_score(category=RiskCategory.MEWS),
            "qsofa": make_risk_score(category=RiskCategory.QSOFA),
            "sofa_simplified": make_risk_score(category=RiskCategory.SOFA_SIMPLIFIED),
        }
        port = FakeRiskScoringPort(
            news2=scores["news2"],
            mews=scores["mews"],
            qsofa=scores["qsofa"],
            sofa_simplified=scores["sofa_simplified"],
        )
        service = RiskScoringService(scoring_port=port)

        result = service.compute_standardized_scores(make_vital_signs(), ())

        assert len(result) == 4
        assert {score.category for score in result} == {
            RiskCategory.NEWS2,
            RiskCategory.MEWS,
            RiskCategory.QSOFA,
            RiskCategory.SOFA_SIMPLIFIED,
        }
