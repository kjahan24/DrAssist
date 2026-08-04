"""`DefaultConfidenceCalculator` — the one concrete
`ConfidenceCalculatorPort` implementation this task ships. See that
port's own docstring (`application/ports.py`) for why an AI-reported
value is trusted as-is and this formula only runs as a fallback.

The fallback formula is a simple, defensible heuristic: start from a
neutral midpoint, add a small amount per supporting evidence item
(diminishing via the cap), subtract a larger amount per contradicting
item (contradictions should hurt confidence more than an equal amount of
support helps it — clinical caution), and subtract a smaller amount per
missing-information gap, clamped to a `[0.05, 0.95]` range so a fallback
score is never reported as either perfectly certain or entirely
worthless.
"""

from app.modules.medical_reasoning_ai.application.ports import ConfidenceCalculatorPort

_BASE_CONFIDENCE = 0.5
_SUPPORTING_WEIGHT = 0.05
_CONTRADICTING_WEIGHT = 0.08
_MISSING_INFORMATION_WEIGHT = 0.03
_MIN_CONFIDENCE = 0.05
_MAX_CONFIDENCE = 0.95


class DefaultConfidenceCalculator(ConfidenceCalculatorPort):
    def calculate_confidence(
        self,
        *,
        ai_reported: float | None,
        supporting_count: int,
        contradicting_count: int,
        missing_information_count: int,
    ) -> float:
        if ai_reported is not None:
            return ai_reported
        score = (
            _BASE_CONFIDENCE
            + (_SUPPORTING_WEIGHT * supporting_count)
            - (_CONTRADICTING_WEIGHT * contradicting_count)
            - (_MISSING_INFORMATION_WEIGHT * missing_information_count)
        )
        return max(_MIN_CONFIDENCE, min(_MAX_CONFIDENCE, score))
