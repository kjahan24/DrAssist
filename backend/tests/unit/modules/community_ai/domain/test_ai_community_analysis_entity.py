"""Unit tests for the `AICommunityAnalysis` aggregate: the
PENDING -> PROCESSING -> COMPLETED | FAILED lifecycle and its guards."""

from uuid import uuid4

import pytest

from app.modules.community_ai.domain.entities import AICommunityAnalysis
from app.modules.community_ai.domain.enums import (
    AIAnalysisStatus,
    AIAnalysisType,
    CommunityContentTargetType,
)
from app.modules.community_ai.domain.events import (
    AIAnalysisCompleted,
    AIAnalysisFailed,
    AIAnalysisRequested,
)
from app.modules.community_ai.domain.exceptions import (
    AnalysisAlreadyProcessingError,
    AnalysisNotProcessingError,
)


def _make_analysis(**overrides: object) -> AICommunityAnalysis:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "analysis_type": AIAnalysisType.SUMMARY,
        "target_type": CommunityContentTargetType.POST,
        "target_id": uuid4(),
    }
    defaults.update(overrides)
    return AICommunityAnalysis.request(**defaults)  # type: ignore[arg-type]


class TestRequest:
    def test_defaults_to_pending_status(self) -> None:
        analysis = _make_analysis()
        assert analysis.status is AIAnalysisStatus.PENDING

    def test_defaults_result_fields_to_none(self) -> None:
        analysis = _make_analysis()
        assert analysis.result is None
        assert analysis.confidence_score is None
        assert analysis.ai_provider is None
        assert analysis.ai_model is None
        assert analysis.error_message is None

    def test_records_an_analysis_requested_event(self) -> None:
        analysis = _make_analysis()
        events = analysis.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], AIAnalysisRequested)
        assert events[0].analysis_id == analysis.id


class TestMarkProcessing:
    def test_moves_to_processing(self) -> None:
        analysis = _make_analysis()
        analysis.mark_processing()
        assert analysis.status is AIAnalysisStatus.PROCESSING

    def test_clears_a_prior_error_message(self) -> None:
        analysis = _make_analysis()
        analysis.mark_processing()
        analysis.mark_failed("Provider timed out.")
        analysis.mark_processing()
        assert analysis.error_message is None

    def test_allowed_from_completed_for_a_refresh(self) -> None:
        analysis = _make_analysis()
        analysis.mark_processing()
        analysis.mark_completed(
            result={"key_points": ["a"]},
            confidence_score=0.8,
            ai_provider="mock",
            ai_model="mock-model",
        )
        analysis.mark_processing()
        assert analysis.status is AIAnalysisStatus.PROCESSING

    def test_allowed_from_failed_for_a_retry(self) -> None:
        analysis = _make_analysis()
        analysis.mark_processing()
        analysis.mark_failed("Provider unavailable.")
        analysis.mark_processing()
        assert analysis.status is AIAnalysisStatus.PROCESSING

    def test_raises_when_already_processing(self) -> None:
        analysis = _make_analysis()
        analysis.mark_processing()
        with pytest.raises(AnalysisAlreadyProcessingError):
            analysis.mark_processing()


class TestMarkCompleted:
    def test_stores_the_result_and_metadata(self) -> None:
        analysis = _make_analysis()
        analysis.mark_processing()
        analysis.mark_completed(
            result={"key_points": ["Point one."]},
            confidence_score=0.75,
            ai_provider="openai",
            ai_model="gpt-4o-mini",
            latency_ms=420.5,
        )
        assert analysis.status is AIAnalysisStatus.COMPLETED
        assert analysis.result == {"key_points": ["Point one."]}
        assert analysis.confidence_score == 0.75
        assert analysis.ai_provider == "openai"
        assert analysis.ai_model == "gpt-4o-mini"
        assert analysis.latency_ms == 420.5

    def test_records_an_analysis_completed_event(self) -> None:
        analysis = _make_analysis()
        analysis.mark_processing()
        analysis.pull_events()
        analysis.mark_completed(
            result={"key_points": []},
            confidence_score=0.5,
            ai_provider="mock",
            ai_model="mock-model",
        )
        events = analysis.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], AIAnalysisCompleted)

    def test_raises_when_not_processing(self) -> None:
        analysis = _make_analysis()
        with pytest.raises(AnalysisNotProcessingError):
            analysis.mark_completed(
                result={}, confidence_score=None, ai_provider="mock", ai_model="mock-model"
            )

    def test_raises_when_already_completed(self) -> None:
        analysis = _make_analysis()
        analysis.mark_processing()
        analysis.mark_completed(
            result={}, confidence_score=None, ai_provider="mock", ai_model="mock-model"
        )
        with pytest.raises(AnalysisNotProcessingError):
            analysis.mark_completed(
                result={}, confidence_score=None, ai_provider="mock", ai_model="mock-model"
            )

    def test_confidence_score_may_be_none(self) -> None:
        analysis = _make_analysis()
        analysis.mark_processing()
        analysis.mark_completed(
            result={"claims": []}, confidence_score=None, ai_provider="mock", ai_model="mock-model"
        )
        assert analysis.confidence_score is None


class TestMarkFailed:
    def test_stores_the_error_message(self) -> None:
        analysis = _make_analysis()
        analysis.mark_processing()
        analysis.mark_failed("AI provider timed out.")
        assert analysis.status is AIAnalysisStatus.FAILED
        assert analysis.error_message == "AI provider timed out."

    def test_records_an_analysis_failed_event(self) -> None:
        analysis = _make_analysis()
        analysis.mark_processing()
        analysis.pull_events()
        analysis.mark_failed("AI provider timed out.")
        events = analysis.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], AIAnalysisFailed)
        assert events[0].error_message == "AI provider timed out."

    def test_raises_when_not_processing(self) -> None:
        analysis = _make_analysis()
        with pytest.raises(AnalysisNotProcessingError):
            analysis.mark_failed("Too early.")

    def test_leaves_result_fields_untouched(self) -> None:
        analysis = _make_analysis()
        analysis.mark_processing()
        analysis.mark_failed("AI provider timed out.")
        assert analysis.result is None
        assert analysis.confidence_score is None
