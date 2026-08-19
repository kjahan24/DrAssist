"""Sanity tests confirming every domain exception carries the identifying
fields its raising site relies on."""

from uuid import uuid4

from app.modules.community_ai.domain.enums import AIAnalysisType, CommunityContentTargetType
from app.modules.community_ai.domain.exceptions import (
    AnalysisAlreadyProcessingError,
    AnalysisNotFoundError,
    AnalysisNotProcessingError,
    AnalysisNotYetCompletedError,
    AnalysisTargetNotFoundError,
    EmbeddingUnavailableError,
    EmptyThreadError,
    InvalidAnalysisResultError,
    UnsupportedAnalysisTargetTypeError,
)


class TestExceptionsCarryIdentifyingFields:
    def test_analysis_not_found(self) -> None:
        analysis_id = uuid4()
        exc = AnalysisNotFoundError(analysis_id)
        assert exc.analysis_id == analysis_id
        assert str(analysis_id) in str(exc)

    def test_analysis_target_not_found(self) -> None:
        target_id = uuid4()
        exc = AnalysisTargetNotFoundError(target_id)
        assert exc.target_id == target_id

    def test_unsupported_analysis_target_type(self) -> None:
        exc = UnsupportedAnalysisTargetTypeError(
            CommunityContentTargetType.COMMENT, AIAnalysisType.RESOURCE_RECOMMENDATION
        )
        assert exc.target_type is CommunityContentTargetType.COMMENT
        assert exc.analysis_type is AIAnalysisType.RESOURCE_RECOMMENDATION
        assert "comment" in str(exc)
        assert "resource_recommendation" in str(exc)

    def test_empty_thread(self) -> None:
        root_comment_id = uuid4()
        exc = EmptyThreadError(root_comment_id)
        assert exc.root_comment_id == root_comment_id

    def test_analysis_already_processing(self) -> None:
        analysis_id = uuid4()
        exc = AnalysisAlreadyProcessingError(analysis_id)
        assert exc.analysis_id == analysis_id

    def test_analysis_not_processing(self) -> None:
        analysis_id = uuid4()
        exc = AnalysisNotProcessingError(analysis_id)
        assert exc.analysis_id == analysis_id

    def test_analysis_not_yet_completed(self) -> None:
        analysis_id = uuid4()
        exc = AnalysisNotYetCompletedError(analysis_id)
        assert exc.analysis_id == analysis_id

    def test_invalid_analysis_result(self) -> None:
        exc = InvalidAnalysisResultError("missing 'key_points' field")
        assert "key_points" in str(exc)

    def test_embedding_unavailable(self) -> None:
        target_id = uuid4()
        exc = EmbeddingUnavailableError(target_id)
        assert exc.target_id == target_id
