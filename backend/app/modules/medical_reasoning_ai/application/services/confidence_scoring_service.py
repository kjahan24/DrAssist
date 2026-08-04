"""`ConfidenceScoringService` — the "confidence scoring" and "uncertainty
estimation" half of this task's own "REASONING ENGINE" section. See
`app.modules.medical_reasoning_ai.application.ports.ConfidenceCalculatorPort`'s
own docstring for the full reasoning on why an AI-reported value is
trusted as-is and a deterministic fallback is only computed when one is
missing.

Applied independently to each of this task's own three named confidence
dimensions ("Clinical Confidence", "Diagnostic Confidence", "Therapeutic
Confidence") by `GenerateClinicalReasoningUseCase`, using the same
aggregate evidence counts for all three — this task's own OUTPUT
specification asks for three confidence *numbers*, not three separately
tracked evidence pools, so scoring each dimension from the same evidence
picture is the direct, unembellished reading of that requirement.

`estimate_uncertainty` is a pure inverse of confidence (`1.0 -
confidence`) — this task's OUTPUT specification does not name a
separate "uncertainty" field, so this is exposed as a reusable
computation (per this module's own "centralize clinical reasoning so no
AI module duplicates reasoning logic" charter) rather than forced into
an unrequested result field.
"""

from app.modules.medical_reasoning_ai.application.ports import ConfidenceCalculatorPort


class ConfidenceScoringService:
    def __init__(self, *, calculator: ConfidenceCalculatorPort) -> None:
        self._calculator = calculator

    def score(
        self,
        *,
        ai_reported: float | None,
        supporting_count: int,
        contradicting_count: int,
        missing_information_count: int,
    ) -> float:
        return self._calculator.calculate_confidence(
            ai_reported=ai_reported,
            supporting_count=supporting_count,
            contradicting_count=contradicting_count,
            missing_information_count=missing_information_count,
        )

    def estimate_uncertainty(self, confidence: float) -> float:
        return 1.0 - confidence
