"""Validation tests for the Community AI Features module's Pydantic v2
response schemas — in particular, that `ai_disclaimer` is always present
regardless of what the underlying DTO carries (see `schemas.py`'s own
docstring for why that's a structural, non-AI-controlled constant)."""

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.community_ai.application.dto import AICommunityAnalysisSummaryDTO
from app.modules.community_ai.domain.enums import (
    AIAnalysisStatus,
    AIAnalysisType,
    CommunityContentTargetType,
)
from app.modules.community_ai.domain.value_objects import SimilarDiscussion
from app.modules.community_ai.presentation.schemas import (
    AICommunityAnalysisFeedResponse,
    AICommunityAnalysisResponse,
    SimilarDiscussionFeedResponse,
    SimilarDiscussionResponse,
)


def _dto(**overrides: object) -> AICommunityAnalysisSummaryDTO:
    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "analysis_id": uuid4(),
        "organization_id": uuid4(),
        "analysis_type": AIAnalysisType.SUMMARY,
        "target_type": CommunityContentTargetType.POST,
        "target_id": uuid4(),
        "status": AIAnalysisStatus.COMPLETED,
        "created_at": now,
        "updated_at": now,
        "result": {"key_points": []},
    }
    defaults.update(overrides)
    return AICommunityAnalysisSummaryDTO(**defaults)  # type: ignore[arg-type]


class TestAICommunityAnalysisResponse:
    def test_maps_the_dto_id_property_to_the_response_id_field(self) -> None:
        dto = _dto()
        response = AICommunityAnalysisResponse.model_validate(dto)
        assert response.id == dto.analysis_id

    def test_always_carries_a_non_empty_ai_disclaimer(self) -> None:
        response = AICommunityAnalysisResponse.model_validate(_dto())
        assert "AI-generated" in response.ai_disclaimer
        assert "diagnosis" in response.ai_disclaimer

    def test_pending_analysis_has_no_result_yet(self) -> None:
        dto = _dto(status=AIAnalysisStatus.PENDING, result=None)
        response = AICommunityAnalysisResponse.model_validate(dto)
        assert response.result is None
        assert response.status is AIAnalysisStatus.PENDING

    def test_feed_response_wraps_a_list_of_items(self) -> None:
        feed = AICommunityAnalysisFeedResponse(
            items=[AICommunityAnalysisResponse.model_validate(_dto())], next_cursor="abc"
        )
        assert len(feed.items) == 1
        assert feed.next_cursor == "abc"


class TestSimilarDiscussionResponse:
    def test_maps_from_the_value_object(self) -> None:
        vo = SimilarDiscussion(
            target_type=CommunityContentTargetType.QUESTION,
            target_id=uuid4(),
            similarity_score=0.5,
        )
        response = SimilarDiscussionResponse.model_validate(vo)
        assert response.target_type is CommunityContentTargetType.QUESTION
        assert response.similarity_score == 0.5

    def test_feed_response_carries_a_disclaimer_too(self) -> None:
        feed = SimilarDiscussionFeedResponse(analysis_id=uuid4(), items=[])
        assert "AI-generated" in feed.ai_disclaimer
