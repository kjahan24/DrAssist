"""`DefaultPathologyInterpretationParser` — the one concrete
`PathologyInterpretationParserPort` implementation this task ships, per
this task's own PARSING section ("robust parser supporting: structured
JSON, markdown, plain text").

Reuses `app.shared.infrastructure.text_processing.json_extraction
.extract_json_object` for the mechanical fence-stripping/`json.loads`
work (rule: "Reuse... Shared parser framework... Avoid duplicate
implementations") — this single JSON-extraction pass is what makes the
parser "robust" across JSON, fenced-markdown-JSON, and JSON embedded in
otherwise free-form text: the AI is always prompted for one fixed-shape
JSON object (the `_JSON_CONTRACT` in `infrastructure/prompts
/templates.py`) regardless of `output_format`; markdown/plain-text
*rendering* is a separate, later concern
(`application/services/pathology_summary_service
.PathologySummaryService.render`), the same "generation produces
structure; rendering produces presentation" split every prior AI
module's own parser establishes for itself.

Missing/malformed fields become an empty string/tuple, `None`
(`confidence_score`), or a lenient default (`category` defaults to
`PathologyFindingCategory.ATYPICAL` — a finding the AI bothered to
report but could not be classified is safer treated as needing
attention than silently downgraded to `BENIGN`) — never a parse
failure. "Duplicated findings"/"hallucinated findings"/"inconsistent
conclusions"/"invalid confidence values" are
`PathologyInterpretationValidatorPort`'s job (per this task's own
VALIDATION section), so this parser stays purely mechanical: a
top-level JSON object that isn't the expected shape, or isn't parseable
JSON at all, is the only thing that fails parsing itself.
"""

from app.modules.pathology_interpretation_ai.application.ports import (
    PathologyInterpretationParserPort,
)
from app.modules.pathology_interpretation_ai.domain.enums import (
    PathologyFindingCategory,
    PathologyOutputFormat,
)
from app.modules.pathology_interpretation_ai.domain.exceptions import (
    InvalidPathologyInterpretationResponseFormatError,
)
from app.modules.pathology_interpretation_ai.domain.value_objects import (
    PathologyFinding,
    PathologyInterpretationResult,
)
from app.shared.infrastructure.text_processing.json_extraction import extract_json_object


class DefaultPathologyInterpretationParser(PathologyInterpretationParserPort):
    def parse(
        self, raw_text: str, *, output_format: PathologyOutputFormat
    ) -> PathologyInterpretationResult:
        try:
            payload = extract_json_object(raw_text)
        except ValueError as exc:
            raise InvalidPathologyInterpretationResponseFormatError(str(exc)) from exc

        raw_findings = payload.get("microscopic_findings")
        findings = (
            tuple(self._parse_finding(item) for item in raw_findings if isinstance(item, dict))
            if isinstance(raw_findings, list)
            else ()
        )

        return PathologyInterpretationResult(
            pathology_summary=str(payload.get("pathology_summary", "") or "").strip(),
            key_findings=self._parse_string_list(payload.get("key_findings")),
            microscopic_findings=findings,
            final_impression=str(payload.get("final_impression", "") or "").strip(),
            clinical_significance=str(payload.get("clinical_significance", "") or "").strip(),
            correlation_recommendations=self._parse_string_list(
                payload.get("correlation_recommendations")
            ),
            suggested_follow_up=self._parse_string_list(payload.get("suggested_follow_up")),
            suggested_specialist_referral=self._parse_string_list(
                payload.get("suggested_specialist_referral")
            ),
            red_flag_warnings=self._parse_string_list(payload.get("red_flag_warnings")),
            confidence_score=self._parse_confidence(payload.get("confidence_score")),
            clinical_reasoning=str(payload.get("clinical_reasoning", "") or "").strip(),
            raw_text=raw_text,
            output_format=output_format,
        )

    def _parse_finding(self, item: dict[str, object]) -> PathologyFinding:
        return PathologyFinding(
            description=str(item.get("description", "") or "").strip(),
            category=self._parse_category(item.get("category")),
            anatomical_site=self._parse_optional_str(item.get("anatomical_site")),
        )

    def _parse_optional_str(self, value: object) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    def _parse_category(self, value: object) -> PathologyFindingCategory:
        if isinstance(value, str):
            try:
                return PathologyFindingCategory(value.strip().lower())
            except ValueError:
                return PathologyFindingCategory.ATYPICAL
        return PathologyFindingCategory.ATYPICAL

    def _parse_confidence(self, value: object) -> float | None:
        """Deliberately **not** clamped to `[0.0, 1.0]` here — this
        task's own VALIDATION section explicitly names "invalid
        confidence values" as its own category, so an out-of-range
        AI-reported value is passed through as-is and left for
        `PathologyInterpretationValidatorPort` to reject
        (`InvalidPathologyConfidenceValueError`), the same "parsing
        stays purely mechanical; content-level checks belong to the
        validator" split this parser's own module docstring documents."""
        if isinstance(value, bool):
            return None
        if isinstance(value, int | float):
            return float(value)
        return None

    def _parse_string_list(self, value: object) -> tuple[str, ...]:
        if not isinstance(value, list):
            return ()
        return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
