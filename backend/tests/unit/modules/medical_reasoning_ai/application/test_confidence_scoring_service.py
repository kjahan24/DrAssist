"""Unit tests for `ConfidenceScoringService` — the "confidence scoring"
and "uncertainty estimation" half of this task's own "REASONING ENGINE"
section."""

import pytest

from app.modules.medical_reasoning_ai.application.services.confidence_scoring_service import (
    ConfidenceScoringService,
)
from tests.unit.modules.medical_reasoning_ai.application.fakes import FakeConfidenceCalculatorPort


class TestScore:
    def test_delegates_to_the_calculator(self) -> None:
        calculator = FakeConfidenceCalculatorPort(fallback_value=0.42)
        service = ConfidenceScoringService(calculator=calculator)

        score = service.score(
            ai_reported=None,
            supporting_count=2,
            contradicting_count=1,
            missing_information_count=0,
        )

        assert score == 0.42
        assert calculator.calls[0]["supporting_count"] == 2

    def test_trusts_ai_reported_value_when_present(self) -> None:
        calculator = FakeConfidenceCalculatorPort(fallback_value=0.42)
        service = ConfidenceScoringService(calculator=calculator)

        score = service.score(
            ai_reported=0.85,
            supporting_count=0,
            contradicting_count=0,
            missing_information_count=0,
        )

        assert score == 0.85


class TestEstimateUncertainty:
    def test_is_the_inverse_of_confidence(self) -> None:
        service = ConfidenceScoringService(calculator=FakeConfidenceCalculatorPort())
        assert service.estimate_uncertainty(0.7) == pytest.approx(0.3)

    def test_zero_confidence_is_full_uncertainty(self) -> None:
        service = ConfidenceScoringService(calculator=FakeConfidenceCalculatorPort())
        assert service.estimate_uncertainty(0.0) == 1.0

    def test_full_confidence_is_zero_uncertainty(self) -> None:
        service = ConfidenceScoringService(calculator=FakeConfidenceCalculatorPort())
        assert service.estimate_uncertainty(1.0) == 0.0
