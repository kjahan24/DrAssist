"""`DefaultRiskStratificationAnalysisParser` — the one concrete
`RiskStratificationAnalysisParserPort` implementation this task ships,
per this task's own PARSING/OUTPUT sections ("Support: JSON, Markdown,
Plain text").

Reuses `app.shared.infrastructure.text_processing.json_extraction
.extract_json_object` for the mechanical fence-stripping/`json.loads`
work (rule: "Reuse... Shared parser... Avoid duplicate implementations")
— the AI is always prompted for one fixed-shape JSON object (the
`_JSON_CONTRACT` in `infrastructure/prompts/templates.py`) regardless of
`output_format`; markdown/plain-text *rendering* is a separate, later
concern (`application/services/risk_report_renderer
.RiskReportRenderer.render`), the same "generation produces structure;
rendering produces presentation" split every prior AI module's own
parser establishes for itself.

Missing/malformed fields become an empty string/tuple, `None`
(`confidence_score`, `score_value`), or a lenient default
(`overall_risk_level` defaults to `OverallRiskLevel.MODERATE` — a
deliberately cautious middle value, never silently `LOW`; an
unparseable risk-score `category` defaults to
`RiskCategory.GENERAL_CLINICAL_DETERIORATION`, this task's own explicit
catch-all category) — never a parse failure. "Invalid scores"/
"hallucinated risk factors"/"invalid confidence" are
`RiskStratificationAnalysisValidatorPort`'s job (per this task's own
VALIDATION section), so this parser stays purely mechanical: a
top-level JSON object that isn't the expected shape, or isn't parseable
JSON at all, is the only thing that fails parsing itself.
"""

from app.modules.risk_stratification_ai.application.ports import (
    RiskStratificationAnalysisParserPort,
)
from app.modules.risk_stratification_ai.domain.enums import (
    OverallRiskLevel,
    RiskCategory,
    RiskStratificationOutputFormat,
)
from app.modules.risk_stratification_ai.domain.exceptions import (
    InvalidRiskStratificationResponseFormatError,
)
from app.modules.risk_stratification_ai.domain.value_objects import (
    RiskScore,
    RiskStratificationResult,
)
from app.shared.infrastructure.text_processing.json_extraction import extract_json_object


class DefaultRiskStratificationAnalysisParser(RiskStratificationAnalysisParserPort):
    def parse(
        self, raw_text: str, *, output_format: RiskStratificationOutputFormat
    ) -> RiskStratificationResult:
        try:
            payload = extract_json_object(raw_text)
        except ValueError as exc:
            raise InvalidRiskStratificationResponseFormatError(str(exc)) from exc

        raw_risk_scores = payload.get("risk_scores")
        risk_scores = (
            tuple(
                self._parse_risk_score(item) for item in raw_risk_scores if isinstance(item, dict)
            )
            if isinstance(raw_risk_scores, list)
            else ()
        )

        return RiskStratificationResult(
            overall_risk_level=self._parse_overall_risk_level(payload.get("overall_risk_level")),
            risk_scores=risk_scores,
            early_warning_indicators=self._parse_string_list(
                payload.get("early_warning_indicators")
            ),
            recommended_monitoring=self._parse_string_list(payload.get("recommended_monitoring")),
            suggested_escalation=self._parse_string_list(payload.get("suggested_escalation")),
            suggested_follow_up=self._parse_string_list(payload.get("suggested_follow_up")),
            red_flag_alerts=self._parse_string_list(payload.get("red_flag_alerts")),
            clinical_reasoning=str(payload.get("clinical_reasoning", "") or "").strip(),
            confidence_score=self._parse_confidence(payload.get("confidence_score")),
            raw_text=raw_text,
            output_format=output_format,
        )

    def _parse_risk_score(self, item: dict[str, object]) -> RiskScore:
        return RiskScore(
            category=self._parse_category(item.get("category")),
            score_value=self._parse_score_value(item.get("score_value")),
            contributing_factors=self._parse_string_list(item.get("contributing_factors")),
            clinical_explanation=str(item.get("clinical_explanation", "") or "").strip(),
        )

    def _parse_overall_risk_level(self, value: object) -> OverallRiskLevel:
        if isinstance(value, str):
            try:
                return OverallRiskLevel(value.strip().lower())
            except ValueError:
                return OverallRiskLevel.MODERATE
        return OverallRiskLevel.MODERATE

    def _parse_category(self, value: object) -> RiskCategory:
        if isinstance(value, str):
            try:
                return RiskCategory(value.strip().lower())
            except ValueError:
                return RiskCategory.GENERAL_CLINICAL_DETERIORATION
        return RiskCategory.GENERAL_CLINICAL_DETERIORATION

    def _parse_score_value(self, value: object) -> float | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int | float):
            return float(value)
        return None

    def _parse_confidence(self, value: object) -> float | None:
        """Deliberately **not** clamped to `[0.0, 1.0]` here — this
        task's own VALIDATION section explicitly names "invalid
        confidence" as its own category, so an out-of-range AI-reported
        value is passed through as-is and left for
        `RiskStratificationAnalysisValidatorPort` to reject
        (`InvalidRiskConfidenceValueError`), the same "parsing stays
        purely mechanical; content-level checks belong to the validator"
        split this parser's own module docstring documents."""
        if isinstance(value, bool):
            return None
        if isinstance(value, int | float):
            return float(value)
        return None

    def _parse_string_list(self, value: object) -> tuple[str, ...]:
        if not isinstance(value, list):
            return ()
        return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
