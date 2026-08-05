"""`DefaultRadiologyInterpretationParser` — the one concrete
`RadiologyInterpretationParserPort` implementation this task ships, per
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
(`application/services/radiology_summary_service
.RadiologySummaryService.render`), the same "generation produces
structure; rendering produces presentation" split every prior AI
module's own parser establishes for itself.

Missing/malformed fields become an empty string/tuple, `None`
(`confidence_score`), or a lenient default (`category` defaults to
`RadiologyFindingCategory.ABNORMAL` — a finding the AI bothered to
report but could not be classified is safer treated as noteworthy than
silently downgraded to `NORMAL`) — never a parse failure. "Duplicated
findings"/"hallucinated findings"/"inconsistent recommendations"/
"invalid confidence values" are `RadiologyInterpretationValidatorPort`'s
job (per this task's own VALIDATION section), so this parser stays
purely mechanical: a top-level JSON object that isn't the expected
shape, or isn't parseable JSON at all, is the only thing that fails
parsing itself.
"""

from app.modules.radiology_interpretation_ai.application.ports import (
    RadiologyInterpretationParserPort,
)
from app.modules.radiology_interpretation_ai.domain.enums import (
    RadiologyFindingCategory,
    RadiologyOutputFormat,
)
from app.modules.radiology_interpretation_ai.domain.exceptions import (
    InvalidRadiologyInterpretationResponseFormatError,
)
from app.modules.radiology_interpretation_ai.domain.value_objects import (
    RadiologyFinding,
    RadiologyInterpretationResult,
)
from app.shared.infrastructure.text_processing.json_extraction import extract_json_object


class DefaultRadiologyInterpretationParser(RadiologyInterpretationParserPort):
    def parse(
        self, raw_text: str, *, output_format: RadiologyOutputFormat
    ) -> RadiologyInterpretationResult:
        try:
            payload = extract_json_object(raw_text)
        except ValueError as exc:
            raise InvalidRadiologyInterpretationResponseFormatError(str(exc)) from exc

        raw_findings = payload.get("findings")
        findings = (
            tuple(self._parse_finding(item) for item in raw_findings if isinstance(item, dict))
            if isinstance(raw_findings, list)
            else ()
        )

        return RadiologyInterpretationResult(
            examination_summary=str(payload.get("examination_summary", "") or "").strip(),
            findings=findings,
            clinical_significance=str(payload.get("clinical_significance", "") or "").strip(),
            differential_imaging_considerations=self._parse_string_list(
                payload.get("differential_imaging_considerations")
            ),
            suggested_follow_up_imaging=self._parse_string_list(
                payload.get("suggested_follow_up_imaging")
            ),
            suggested_specialist_referral=self._parse_string_list(
                payload.get("suggested_specialist_referral")
            ),
            red_flag_warnings=self._parse_string_list(payload.get("red_flag_warnings")),
            confidence_score=self._parse_confidence(payload.get("confidence_score")),
            clinical_reasoning=str(payload.get("clinical_reasoning", "") or "").strip(),
            raw_text=raw_text,
            output_format=output_format,
        )

    def _parse_finding(self, item: dict[str, object]) -> RadiologyFinding:
        return RadiologyFinding(
            description=str(item.get("description", "") or "").strip(),
            category=self._parse_category(item.get("category")),
            anatomical_region=self._parse_optional_str(item.get("anatomical_region")),
        )

    def _parse_optional_str(self, value: object) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    def _parse_category(self, value: object) -> RadiologyFindingCategory:
        if isinstance(value, str):
            try:
                return RadiologyFindingCategory(value.strip().lower())
            except ValueError:
                return RadiologyFindingCategory.ABNORMAL
        return RadiologyFindingCategory.ABNORMAL

    def _parse_confidence(self, value: object) -> float | None:
        """Deliberately **not** clamped to `[0.0, 1.0]` here, unlike
        `app.modules.lab_interpretation_ai`'s own parser — this task's
        own VALIDATION section explicitly names "invalid confidence
        values" as its own category, so an out-of-range AI-reported value
        is passed through as-is and left for
        `RadiologyInterpretationValidatorPort` to reject
        (`InvalidRadiologyConfidenceValueError`), the same "parsing
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
