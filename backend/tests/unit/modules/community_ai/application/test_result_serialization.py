"""Unit tests for `_result_serialization.py`'s round-trip conversions."""

from uuid import uuid4

from app.modules.community_ai.application.services._result_serialization import (
    misinformation_assessment_from_dict,
    misinformation_assessment_to_dict,
    resource_recommendations_from_dict,
    resource_recommendations_to_dict,
    similar_discussions_from_dict,
    similar_discussions_to_dict,
    summary_from_dict,
    summary_to_dict,
)
from app.modules.community_ai.domain.enums import CommunityContentTargetType
from app.modules.community_ai.domain.value_objects import SimilarDiscussion
from tests.unit.modules.community_ai.application.fakes import (
    make_misinformation_assessment,
    make_resource_recommendation,
    make_summary,
)


class TestSummaryRoundTrip:
    def test_round_trips_through_dict(self) -> None:
        summary = make_summary(key_points=("A", "B"), safety_disclaimer="Consult a doctor.")
        assert summary_from_dict(summary_to_dict(summary)) == summary


class TestSimilarDiscussionsRoundTrip:
    def test_round_trips_a_uuid_target_id_through_a_plain_string(self) -> None:
        items = (
            SimilarDiscussion(
                target_type=CommunityContentTargetType.QUESTION,
                target_id=uuid4(),
                similarity_score=0.42,
            ),
        )
        data = similar_discussions_to_dict(items)
        assert isinstance(data["items"][0]["target_id"], str)

        restored = similar_discussions_from_dict(data)
        assert restored == items

    def test_missing_items_key_defaults_to_empty(self) -> None:
        assert similar_discussions_from_dict({}) == ()


class TestResourceRecommendationsRoundTrip:
    def test_round_trips_through_dict(self) -> None:
        items = (make_resource_recommendation(),)
        assert resource_recommendations_from_dict(resource_recommendations_to_dict(items)) == items

    def test_missing_items_key_defaults_to_empty(self) -> None:
        assert resource_recommendations_from_dict({}) == ()


class TestMisinformationAssessmentRoundTrip:
    def test_round_trips_through_dict(self) -> None:
        assessment = make_misinformation_assessment(claims=("Claim A",))
        assert (
            misinformation_assessment_from_dict(misinformation_assessment_to_dict(assessment))
            == assessment
        )
