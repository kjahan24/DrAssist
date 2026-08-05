"""Tests for `LifestyleRecommendationService`."""

from app.modules.patient_education_ai.application.services.lifestyle_recommendation_service import (  # noqa: E501
    LifestyleRecommendationService,
)
from tests.unit.modules.patient_education_ai.application.fakes import (
    FakeLifestyleRecommendationPort,
)


class TestCollectLifestyleAdvice:
    def test_delegates_to_port(self) -> None:
        port = FakeLifestyleRecommendationPort(lifestyle=("Limit alcohol.",))
        service = LifestyleRecommendationService(lifestyle_recommendation_port=port)

        assert service.collect_lifestyle_advice(("Hypertension",)) == ("Limit alcohol.",)

    def test_empty_when_port_returns_nothing(self) -> None:
        service = LifestyleRecommendationService(
            lifestyle_recommendation_port=FakeLifestyleRecommendationPort()
        )
        assert service.collect_lifestyle_advice(("Unknown",)) == ()


class TestCollectDietAdvice:
    def test_delegates_to_port(self) -> None:
        port = FakeLifestyleRecommendationPort(diet=("Low-sodium diet.",))
        service = LifestyleRecommendationService(lifestyle_recommendation_port=port)

        assert service.collect_diet_advice(("Hypertension",)) == ("Low-sodium diet.",)


class TestCollectExerciseAdvice:
    def test_delegates_to_port(self) -> None:
        port = FakeLifestyleRecommendationPort(exercise=("Moderate aerobic activity.",))
        service = LifestyleRecommendationService(lifestyle_recommendation_port=port)

        assert service.collect_exercise_advice(("Hypertension",)) == ("Moderate aerobic activity.",)


class TestCollectPreventiveCareRecommendations:
    def test_delegates_to_port(self) -> None:
        port = FakeLifestyleRecommendationPort(preventive_care=("Annual eye exam.",))
        service = LifestyleRecommendationService(lifestyle_recommendation_port=port)

        result = service.collect_preventive_care_recommendations(("Diabetes",), 55)

        assert result == ("Annual eye exam.",)

    def test_passes_through_diagnoses_and_age(self) -> None:
        port = FakeLifestyleRecommendationPort()
        service = LifestyleRecommendationService(lifestyle_recommendation_port=port)

        service.collect_preventive_care_recommendations(("Diabetes",), 55)

        assert port.preventive_care_calls == [(("Diabetes",), 55)]

    def test_passes_through_none_age(self) -> None:
        port = FakeLifestyleRecommendationPort()
        service = LifestyleRecommendationService(lifestyle_recommendation_port=port)

        service.collect_preventive_care_recommendations(("Diabetes",), None)

        assert port.preventive_care_calls == [(("Diabetes",), None)]
