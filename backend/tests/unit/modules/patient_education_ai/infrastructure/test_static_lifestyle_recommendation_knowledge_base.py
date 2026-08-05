"""Unit tests for `StaticLifestyleRecommendationKnowledgeBase`."""

import pytest

from app.modules.patient_education_ai.infrastructure.lifestyle_recommendation.static_lifestyle_recommendation_knowledge_base import (  # noqa: E501
    StaticLifestyleRecommendationKnowledgeBase,
)

_KB = StaticLifestyleRecommendationKnowledgeBase()


class TestRecommendLifestyle:
    def test_returns_recommendations_for_a_recognized_diagnosis(self) -> None:
        assert len(_KB.recommend_lifestyle(("Hypertension",))) > 0

    def test_returns_empty_tuple_for_an_unrecognized_diagnosis(self) -> None:
        assert _KB.recommend_lifestyle(("Some Unrecognized Condition",)) == ()

    def test_deduplicates_across_diagnoses(self) -> None:
        result = _KB.recommend_lifestyle(("Hypertension", "Coronary artery disease"))
        assert len(result) == len(set(result))


class TestRecommendDiet:
    def test_returns_recommendations_for_a_recognized_diagnosis(self) -> None:
        assert len(_KB.recommend_diet(("Diabetes",))) > 0

    def test_returns_empty_tuple_for_an_unrecognized_diagnosis(self) -> None:
        assert _KB.recommend_diet(("Some Unrecognized Condition",)) == ()


class TestRecommendExercise:
    def test_returns_recommendations_for_a_recognized_diagnosis(self) -> None:
        assert len(_KB.recommend_exercise(("Stroke",))) > 0

    def test_returns_empty_tuple_for_an_unrecognized_diagnosis(self) -> None:
        assert _KB.recommend_exercise(("Some Unrecognized Condition",)) == ()


class TestRecommendPreventiveCare:
    def test_returns_diagnosis_based_recommendation(self) -> None:
        result = _KB.recommend_preventive_care(("Diabetes",), None)
        assert any("eye exam" in item.lower() for item in result)

    def test_returns_empty_when_nothing_matches_and_age_is_none(self) -> None:
        assert _KB.recommend_preventive_care(("Some Unrecognized Condition",), None) == ()

    def test_flu_vaccine_reminder_for_age_above_threshold(self) -> None:
        result = _KB.recommend_preventive_care((), 30)
        assert any("flu vaccine" in item.lower() for item in result)

    def test_no_flu_vaccine_reminder_for_infant_below_threshold(self) -> None:
        result = _KB.recommend_preventive_care((), 2)
        assert not any("flu vaccine" in item.lower() for item in result)

    def test_pneumonia_vaccine_reminder_for_age_above_threshold(self) -> None:
        result = _KB.recommend_preventive_care((), 70)
        assert any("pneumonia vaccine" in item.lower() for item in result)

    def test_no_pneumonia_vaccine_reminder_below_threshold(self) -> None:
        result = _KB.recommend_preventive_care((), 40)
        assert not any("pneumonia vaccine" in item.lower() for item in result)

    def test_colorectal_screening_reminder_for_age_above_threshold(self) -> None:
        result = _KB.recommend_preventive_care((), 50)
        assert any("colorectal" in item.lower() for item in result)

    def test_no_colorectal_screening_reminder_below_threshold(self) -> None:
        result = _KB.recommend_preventive_care((), 30)
        assert not any("colorectal" in item.lower() for item in result)

    @pytest.mark.parametrize("age", [65, 70, 90])
    def test_older_patients_get_multiple_reminders(self, age: int) -> None:
        result = _KB.recommend_preventive_care((), age)
        assert len(result) >= 3

    def test_combines_diagnosis_and_age_based_recommendations(self) -> None:
        result = _KB.recommend_preventive_care(("Diabetes",), 70)
        assert any("eye exam" in item.lower() for item in result)
        assert any("flu vaccine" in item.lower() for item in result)
