"""Unit tests for `DefaultConfidenceCalculator`."""

from app.modules.medical_reasoning_ai.infrastructure.confidence.default_confidence_calculator import (  # noqa: E501
    DefaultConfidenceCalculator,
)


class TestCalculateConfidence:
    def test_trusts_the_ai_reported_value_when_present(self) -> None:
        calculator = DefaultConfidenceCalculator()

        score = calculator.calculate_confidence(
            ai_reported=0.85,
            supporting_count=0,
            contradicting_count=100,
            missing_information_count=100,
        )

        assert score == 0.85

    def test_computes_a_fallback_when_ai_reported_is_none(self) -> None:
        calculator = DefaultConfidenceCalculator()

        score = calculator.calculate_confidence(
            ai_reported=None,
            supporting_count=0,
            contradicting_count=0,
            missing_information_count=0,
        )

        assert score == 0.5

    def test_more_supporting_evidence_increases_the_fallback_score(self) -> None:
        calculator = DefaultConfidenceCalculator()

        base = calculator.calculate_confidence(
            ai_reported=None, supporting_count=0, contradicting_count=0, missing_information_count=0
        )
        boosted = calculator.calculate_confidence(
            ai_reported=None, supporting_count=3, contradicting_count=0, missing_information_count=0
        )

        assert boosted > base

    def test_more_contradicting_evidence_decreases_the_fallback_score(self) -> None:
        calculator = DefaultConfidenceCalculator()

        base = calculator.calculate_confidence(
            ai_reported=None, supporting_count=0, contradicting_count=0, missing_information_count=0
        )
        reduced = calculator.calculate_confidence(
            ai_reported=None, supporting_count=0, contradicting_count=3, missing_information_count=0
        )

        assert reduced < base

    def test_contradicting_evidence_hurts_more_than_equal_supporting_helps(self) -> None:
        calculator = DefaultConfidenceCalculator()

        supporting_boost = calculator.calculate_confidence(
            ai_reported=None, supporting_count=1, contradicting_count=0, missing_information_count=0
        )
        contradicting_penalty = calculator.calculate_confidence(
            ai_reported=None, supporting_count=0, contradicting_count=1, missing_information_count=0
        )

        supporting_delta = supporting_boost - 0.5
        contradicting_delta = 0.5 - contradicting_penalty
        assert contradicting_delta > supporting_delta

    def test_more_missing_information_decreases_the_fallback_score(self) -> None:
        calculator = DefaultConfidenceCalculator()

        base = calculator.calculate_confidence(
            ai_reported=None, supporting_count=0, contradicting_count=0, missing_information_count=0
        )
        reduced = calculator.calculate_confidence(
            ai_reported=None, supporting_count=0, contradicting_count=0, missing_information_count=3
        )

        assert reduced < base

    def test_fallback_score_never_drops_below_the_floor(self) -> None:
        calculator = DefaultConfidenceCalculator()

        score = calculator.calculate_confidence(
            ai_reported=None,
            supporting_count=0,
            contradicting_count=100,
            missing_information_count=100,
        )

        assert score == 0.05

    def test_fallback_score_never_exceeds_the_ceiling(self) -> None:
        calculator = DefaultConfidenceCalculator()

        score = calculator.calculate_confidence(
            ai_reported=None,
            supporting_count=100,
            contradicting_count=0,
            missing_information_count=0,
        )

        assert score == 0.95
