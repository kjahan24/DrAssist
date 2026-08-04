"""`DefaultLabInterpretationParser` — the one concrete
`LabInterpretationParserPort` implementation this task ships, per this
task's own OUTPUT specification.

Reuses `app.shared.infrastructure.text_processing.json_extraction
.extract_json_object` for the mechanical fence-stripping/`json.loads`
work (rule: "Reuse... Shared parser... Avoid duplicate implementations").

The AI is always prompted for a single fixed-shape JSON object (the
`_JSON_CONTRACT` in `infrastructure/prompts/templates.py`) regardless of
`output_format`; markdown/text are handled at render time instead, the
same "generation produces structure; rendering produces presentation"
split every prior AI module's own parser establishes for itself.

Missing/malformed fields become an empty string/tuple, `None`
(`confidence_score`, `numeric_value`), or a lenient default (`flag`
defaults to `LabFindingFlag.NORMAL`) — never a parse failure. "Missing
reasoning"/"hallucinated values" are `LabInterpretationValidatorPort`'s
job (per this task's own VALIDATION section), so this parser stays
purely mechanical: a top-level JSON object that isn't the expected shape,
or isn't parseable JSON at all, is the only thing that fails parsing
itself.
"""

from app.modules.lab_interpretation_ai.application.ports import LabInterpretationParserPort
from app.modules.lab_interpretation_ai.domain.enums import (
    LabFindingFlag,
    LabInterpretationOutputFormat,
)
from app.modules.lab_interpretation_ai.domain.exceptions import (
    InvalidLabInterpretationResponseFormatError,
)
from app.modules.lab_interpretation_ai.domain.value_objects import (
    LabFinding,
    LabInterpretationResult,
)
from app.shared.infrastructure.text_processing.json_extraction import extract_json_object


class DefaultLabInterpretationParser(LabInterpretationParserPort):
    def parse(
        self, raw_text: str, *, output_format: LabInterpretationOutputFormat
    ) -> LabInterpretationResult:
        try:
            payload = extract_json_object(raw_text)
        except ValueError as exc:
            raise InvalidLabInterpretationResponseFormatError(str(exc)) from exc

        raw_findings = payload.get("findings")
        findings = (
            tuple(self._parse_finding(item) for item in raw_findings if isinstance(item, dict))
            if isinstance(raw_findings, list)
            else ()
        )

        return LabInterpretationResult(
            overall_interpretation=str(payload.get("overall_interpretation", "") or "").strip(),
            findings=findings,
            clinical_significance=str(payload.get("clinical_significance", "") or "").strip(),
            supporting_evidence=self._parse_string_list(payload.get("supporting_evidence")),
            potential_causes=self._parse_string_list(payload.get("potential_causes")),
            suggested_follow_up_tests=self._parse_string_list(
                payload.get("suggested_follow_up_tests")
            ),
            monitoring_recommendations=self._parse_string_list(
                payload.get("monitoring_recommendations")
            ),
            red_flag_warnings=self._parse_string_list(payload.get("red_flag_warnings")),
            confidence_score=self._parse_confidence(payload.get("confidence_score")),
            raw_text=raw_text,
            output_format=output_format,
        )

    def _parse_finding(self, item: dict[str, object]) -> LabFinding:
        return LabFinding(
            test_name=str(item.get("test_name", "") or "").strip(),
            value=str(item.get("value", "") or "").strip(),
            numeric_value=self._parse_numeric_value(item.get("numeric_value")),
            unit=self._parse_optional_str(item.get("unit")),
            flag=self._parse_flag(item.get("flag")),
        )

    def _parse_numeric_value(self, value: object) -> float | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int | float):
            return float(value)
        return None

    def _parse_optional_str(self, value: object) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    def _parse_flag(self, value: object) -> LabFindingFlag:
        if isinstance(value, str):
            try:
                return LabFindingFlag(value.strip().lower())
            except ValueError:
                return LabFindingFlag.NORMAL
        return LabFindingFlag.NORMAL

    def _parse_confidence(self, value: object) -> float | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int | float):
            return max(0.0, min(1.0, float(value)))
        return None

    def _parse_string_list(self, value: object) -> tuple[str, ...]:
        if not isinstance(value, list):
            return ()
        return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
