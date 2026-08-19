"""Unit tests for the Community AI Features module's domain value
objects."""

from uuid import uuid4

import pytest

from app.modules.community_ai.domain.enums import (
    CommunityContentTargetType,
    MisinformationRiskLevel,
    ResourceType,
)
from app.modules.community_ai.domain.value_objects import (
    CommunityDiscussionSummary,
    MisinformationAssessment,
    SimilarDiscussion,
    TrustedMedicalSource,
    TrustedResourceRecommendation,
)


class TestCommunityDiscussionSummary:
    def test_constructs_with_every_field(self) -> None:
        summary = CommunityDiscussionSummary(
            key_points=("Point one.",),
            main_claims=("Claim one.",),
            areas_of_agreement=("Agreement one.",),
            areas_of_disagreement=("Disagreement one.",),
            unanswered_questions=("Question one?",),
            safety_disclaimer="This is not medical advice.",
        )
        assert summary.key_points == ("Point one.",)
        assert summary.safety_disclaimer == "This is not medical advice."

    def test_safety_disclaimer_defaults_to_none(self) -> None:
        summary = CommunityDiscussionSummary(
            key_points=(),
            main_claims=(),
            areas_of_agreement=(),
            areas_of_disagreement=(),
            unanswered_questions=(),
        )
        assert summary.safety_disclaimer is None


class TestSimilarDiscussion:
    def test_constructs_with_a_valid_score(self) -> None:
        target_id = uuid4()
        discussion = SimilarDiscussion(
            target_type=CommunityContentTargetType.POST,
            target_id=target_id,
            similarity_score=0.87,
        )
        assert discussion.target_id == target_id
        assert discussion.similarity_score == 0.87

    def test_accepts_boundary_scores(self) -> None:
        SimilarDiscussion(
            target_type=CommunityContentTargetType.POST, target_id=uuid4(), similarity_score=0.0
        )
        SimilarDiscussion(
            target_type=CommunityContentTargetType.POST, target_id=uuid4(), similarity_score=1.0
        )

    def test_score_above_one_raises(self) -> None:
        with pytest.raises(ValueError, match="similarity_score"):
            SimilarDiscussion(
                target_type=CommunityContentTargetType.POST,
                target_id=uuid4(),
                similarity_score=1.1,
            )

    def test_negative_score_raises(self) -> None:
        with pytest.raises(ValueError, match="similarity_score"):
            SimilarDiscussion(
                target_type=CommunityContentTargetType.POST,
                target_id=uuid4(),
                similarity_score=-0.1,
            )


class TestTrustedMedicalSource:
    def test_constructs_with_defaults(self) -> None:
        source = TrustedMedicalSource(
            title="MedlinePlus", url="https://medlineplus.gov", resource_type=ResourceType.WEBSITE
        )
        assert source.topic_tags == ()


class TestTrustedResourceRecommendation:
    def test_constructs_with_a_valid_score(self) -> None:
        recommendation = TrustedResourceRecommendation(
            source_title="MedlinePlus",
            source_url="https://medlineplus.gov",
            resource_type=ResourceType.WEBSITE,
            relevance_explanation="Covers this exact topic.",
            confidence_score=0.9,
        )
        assert recommendation.confidence_score == 0.9

    def test_score_above_one_raises(self) -> None:
        with pytest.raises(ValueError, match="confidence_score"):
            TrustedResourceRecommendation(
                source_title="MedlinePlus",
                source_url="https://medlineplus.gov",
                resource_type=ResourceType.WEBSITE,
                relevance_explanation="Covers this exact topic.",
                confidence_score=1.5,
            )


class TestMisinformationAssessment:
    def test_constructs_with_every_field(self) -> None:
        assessment = MisinformationAssessment(
            risk_level=MisinformationRiskLevel.HIGH,
            claims=("Unsupported claim.",),
            evidence_needed=True,
            explanation="No credible source supports this claim.",
            confidence_score=0.8,
            recommended_for_moderation_review=True,
            reference_suggestions=("See CDC guidance.",),
        )
        assert assessment.risk_level is MisinformationRiskLevel.HIGH
        assert assessment.recommended_for_moderation_review is True

    def test_reference_suggestions_defaults_to_empty(self) -> None:
        assessment = MisinformationAssessment(
            risk_level=MisinformationRiskLevel.LOW,
            claims=(),
            evidence_needed=False,
            explanation="No concerning claims found.",
            confidence_score=0.6,
            recommended_for_moderation_review=False,
        )
        assert assessment.reference_suggestions == ()

    def test_score_above_one_raises(self) -> None:
        with pytest.raises(ValueError, match="confidence_score"):
            MisinformationAssessment(
                risk_level=MisinformationRiskLevel.LOW,
                claims=(),
                evidence_needed=False,
                explanation="Explanation.",
                confidence_score=2.0,
                recommended_for_moderation_review=False,
            )
