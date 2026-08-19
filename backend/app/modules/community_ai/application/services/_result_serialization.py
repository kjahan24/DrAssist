"""Converts between this module's domain value objects
(`CommunityDiscussionSummary`/`SimilarDiscussion`/
`TrustedResourceRecommendation`/`MisinformationAssessment`) and the plain
`dict[str, Any]` shape `AICommunityAnalysis.result` stores (and
`infrastructure/models.py`'s `JSONB` column persists). Pure functions,
no I/O — kept at the application layer (not `infrastructure/mappers.py`)
because both a write path (`mark_completed(result=...)`) and a read path
(`analysis_query_service.py` deserializing a stored row back into a typed
DTO for a caller) need the identical conversion, and neither is itself an
ORM concern.
"""

from typing import Any
from uuid import UUID

from app.modules.community_ai.domain.enums import (
    CommunityContentTargetType,
    MisinformationRiskLevel,
    ResourceType,
)
from app.modules.community_ai.domain.value_objects import (
    CommunityDiscussionSummary,
    MisinformationAssessment,
    SimilarDiscussion,
    TrustedResourceRecommendation,
)


def summary_to_dict(summary: CommunityDiscussionSummary) -> dict[str, Any]:
    return {
        "key_points": list(summary.key_points),
        "main_claims": list(summary.main_claims),
        "areas_of_agreement": list(summary.areas_of_agreement),
        "areas_of_disagreement": list(summary.areas_of_disagreement),
        "unanswered_questions": list(summary.unanswered_questions),
        "safety_disclaimer": summary.safety_disclaimer,
    }


def summary_from_dict(data: dict[str, Any]) -> CommunityDiscussionSummary:
    return CommunityDiscussionSummary(
        key_points=tuple(data.get("key_points", ())),
        main_claims=tuple(data.get("main_claims", ())),
        areas_of_agreement=tuple(data.get("areas_of_agreement", ())),
        areas_of_disagreement=tuple(data.get("areas_of_disagreement", ())),
        unanswered_questions=tuple(data.get("unanswered_questions", ())),
        safety_disclaimer=data.get("safety_disclaimer"),
    )


def similar_discussions_to_dict(items: tuple[SimilarDiscussion, ...]) -> dict[str, Any]:
    return {
        "items": [
            {
                "target_type": item.target_type.value,
                "target_id": str(item.target_id),
                "similarity_score": item.similarity_score,
            }
            for item in items
        ]
    }


def similar_discussions_from_dict(data: dict[str, Any]) -> tuple[SimilarDiscussion, ...]:
    return tuple(
        SimilarDiscussion(
            target_type=CommunityContentTargetType(item["target_type"]),
            target_id=UUID(item["target_id"]),
            similarity_score=item["similarity_score"],
        )
        for item in data.get("items", ())
    )


def resource_recommendations_to_dict(
    items: tuple[TrustedResourceRecommendation, ...],
) -> dict[str, Any]:
    return {
        "items": [
            {
                "source_title": item.source_title,
                "source_url": item.source_url,
                "resource_type": item.resource_type.value,
                "relevance_explanation": item.relevance_explanation,
                "confidence_score": item.confidence_score,
            }
            for item in items
        ]
    }


def resource_recommendations_from_dict(
    data: dict[str, Any],
) -> tuple[TrustedResourceRecommendation, ...]:
    return tuple(
        TrustedResourceRecommendation(
            source_title=item["source_title"],
            source_url=item["source_url"],
            resource_type=ResourceType(item["resource_type"]),
            relevance_explanation=item["relevance_explanation"],
            confidence_score=item["confidence_score"],
        )
        for item in data.get("items", ())
    )


def misinformation_assessment_to_dict(assessment: MisinformationAssessment) -> dict[str, Any]:
    return {
        "risk_level": assessment.risk_level.value,
        "claims": list(assessment.claims),
        "evidence_needed": assessment.evidence_needed,
        "explanation": assessment.explanation,
        "confidence_score": assessment.confidence_score,
        "recommended_for_moderation_review": assessment.recommended_for_moderation_review,
        "reference_suggestions": list(assessment.reference_suggestions),
    }


def misinformation_assessment_from_dict(data: dict[str, Any]) -> MisinformationAssessment:
    return MisinformationAssessment(
        risk_level=MisinformationRiskLevel(data["risk_level"]),
        claims=tuple(data.get("claims", ())),
        evidence_needed=data["evidence_needed"],
        explanation=data["explanation"],
        confidence_score=data["confidence_score"],
        recommended_for_moderation_review=data["recommended_for_moderation_review"],
        reference_suggestions=tuple(data.get("reference_suggestions", ())),
    )
