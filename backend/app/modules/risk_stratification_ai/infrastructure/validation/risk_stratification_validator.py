"""`DefaultRiskStratificationAnalysisValidator` — the one concrete
`RiskStratificationAnalysisValidatorPort` implementation this task
ships, per this task's own "invalid scores, malformed JSON, hallucinated
risk factors, invalid confidence" VALIDATION categories ("malformed
JSON" is `RiskStratificationAnalysisParserPort`'s concern, and "missing
vital signs"/"incomplete laboratory values" are `domain/value_objects
.py`'s own `__post_init__` concern on the caller-supplied *input* — a
result that reaches this validator already parsed successfully, so only
content-level checks on the AI's own *output* remain here, the same
split every prior AI module's own validator documents for itself).

Checks run in this order, each a distinct failure mode with its own
domain exception:

1. Any `RiskScore.score_value` outside its category's own valid range
   -> `InvalidRiskScoreError`. The four standardized scores each have a
   well-known, fixed range (`NEWS2` 0-20, `MEWS` 0-14, `qSOFA` 0-3,
   `SOFA (simplified)` 0-8 — see `_SCORE_RANGES`); the ten AI-assessed
   categories have no standardized numeric scale, so a `[0.0, 1.0]`
   normalized range is applied to them instead, when the AI chooses to
   populate one (this task's own domain design leaves `score_value`
   optional for those categories — see `RiskScore`'s own docstring —
   so `None` is never itself an error here).
2. `confidence_score` present but outside `[0.0, 1.0]` ->
   `InvalidRiskConfidenceValueError`. `None` is not an error here: this
   module's confidence is always deterministically filled in by
   `MedicalReasoningAIPort.score_confidence` during enrichment (see
   `application/use_cases/analyze_patient_risk.py`), so a missing
   AI-reported value is expected, not invalid.
3. Any hallucinated placeholder in `clinical_reasoning`, any risk
   score's own `clinical_explanation`/`contributing_factors`, or any of
   `early_warning_indicators`/`recommended_monitoring`/
   `suggested_escalation`/`suggested_follow_up`/`red_flag_alerts` ->
   `HallucinatedRiskFactorError`.
"""

from app.modules.risk_stratification_ai.application.ports import (
    RiskStratificationAnalysisValidatorPort,
)
from app.modules.risk_stratification_ai.domain.enums import RiskCategory
from app.modules.risk_stratification_ai.domain.exceptions import (
    HallucinatedRiskFactorError,
    InvalidRiskConfidenceValueError,
    InvalidRiskScoreError,
)
from app.modules.risk_stratification_ai.domain.value_objects import (
    RiskScore,
    RiskStratificationInput,
    RiskStratificationResult,
)
from app.shared.infrastructure.text_processing.placeholder_detection import (
    find_placeholder_marker,
)

_SCORE_RANGES: dict[RiskCategory, tuple[float, float]] = {
    RiskCategory.NEWS2: (0.0, 20.0),
    RiskCategory.MEWS: (0.0, 14.0),
    RiskCategory.QSOFA: (0.0, 3.0),
    RiskCategory.SOFA_SIMPLIFIED: (0.0, 8.0),
}
_DEFAULT_QUALITATIVE_RANGE = (0.0, 1.0)


class DefaultRiskStratificationAnalysisValidator(RiskStratificationAnalysisValidatorPort):
    def validate(
        self, result: RiskStratificationResult, input_dto: RiskStratificationInput
    ) -> None:
        self._check_invalid_scores(result)
        self._check_confidence_value(result)
        self._check_hallucinated_placeholders(result)

    def _check_invalid_scores(self, result: RiskStratificationResult) -> None:
        for score in result.risk_scores:
            if score.score_value is None:
                continue
            low, high = _SCORE_RANGES.get(score.category, _DEFAULT_QUALITATIVE_RANGE)
            if not (low <= score.score_value <= high):
                raise InvalidRiskScoreError(score.category.value, score.score_value)

    def _check_confidence_value(self, result: RiskStratificationResult) -> None:
        if result.confidence_score is not None and not (0.0 <= result.confidence_score <= 1.0):
            raise InvalidRiskConfidenceValueError()

    def _check_risk_score_placeholders(self, score: RiskScore) -> None:
        placeholder = find_placeholder_marker(score.clinical_explanation)
        if placeholder is not None:
            raise HallucinatedRiskFactorError("risk_scores", placeholder)
        for factor in score.contributing_factors:
            placeholder = find_placeholder_marker(factor)
            if placeholder is not None:
                raise HallucinatedRiskFactorError("risk_scores", placeholder)

    def _check_hallucinated_placeholders(self, result: RiskStratificationResult) -> None:
        placeholder = find_placeholder_marker(result.clinical_reasoning)
        if placeholder is not None:
            raise HallucinatedRiskFactorError("clinical_reasoning", placeholder)

        for score in result.risk_scores:
            self._check_risk_score_placeholders(score)

        list_fields = (
            ("early_warning_indicators", result.early_warning_indicators),
            ("recommended_monitoring", result.recommended_monitoring),
            ("suggested_escalation", result.suggested_escalation),
            ("suggested_follow_up", result.suggested_follow_up),
            ("red_flag_alerts", result.red_flag_alerts),
        )
        for field_name, items in list_fields:
            for text in items:
                placeholder = find_placeholder_marker(text)
                if placeholder is not None:
                    raise HallucinatedRiskFactorError(field_name, placeholder)
