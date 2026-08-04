"""`DefaultICD10SuggestionParser` — the one concrete
`ICD10SuggestionParserPort` implementation this task ships, per "OUTPUT
PARSER" (implicit in this task's own OUTPUT specification: "Return
structured ICD suggestions... Each suggestion must contain...").

Reuses `app.shared.infrastructure.text_processing.json_extraction
.extract_json_object` for the mechanical fence-stripping/`json.loads`
work (rule: "Reuse... Shared parser framework... Avoid duplicate
implementations" — see that function's own docstring for why it lives in
the shared kernel rather than a fourth copy of the same regex).

The AI is always prompted for a single fixed-shape JSON object — one
`"suggestions"` array (the `_JSON_CONTRACT` in `infrastructure/prompts
/templates.py`) — regardless of `output_format`; markdown/text are
handled at render time instead
(`application/services/icd10_suggestion_renderer.py`), the same
"generation produces structure; rendering produces presentation" split
`app.modules.soap_note_ai.infrastructure.parsing.soap_note_parser` uses
for itself.

Missing/malformed fields *within* an individual suggestion object become
an empty string (text fields), `None` (confidence score), or default to
`DiagnosisFlag.SECONDARY` (flag) — never a parse failure. "Invalid ICD
codes"/"missing confidence scores" are `ICD10SuggestionValidatorPort`'s
job (per this task's own VALIDATION section), so this parser stays
purely mechanical: a top-level JSON object that isn't `{"suggestions":
[...]}`, or isn't parseable JSON at all, is the only thing that fails
parsing itself.
"""

from app.modules.icd10_ai.application.ports import ICD10SuggestionParserPort
from app.modules.icd10_ai.domain.enums import DiagnosisFlag, ICD10OutputFormat
from app.modules.icd10_ai.domain.exceptions import InvalidICD10ResponseFormatError
from app.modules.icd10_ai.domain.value_objects import ICD10Suggestion, ICD10SuggestionSet
from app.shared.infrastructure.text_processing.json_extraction import extract_json_object


class DefaultICD10SuggestionParser(ICD10SuggestionParserPort):
    def parse(self, raw_text: str, *, output_format: ICD10OutputFormat) -> ICD10SuggestionSet:
        try:
            payload = extract_json_object(raw_text)
        except ValueError as exc:
            raise InvalidICD10ResponseFormatError(str(exc)) from exc

        raw_suggestions = payload.get("suggestions")
        if not isinstance(raw_suggestions, list):
            raise InvalidICD10ResponseFormatError(
                'expected a "suggestions" array in the AI\'s JSON response'
            )

        suggestions = tuple(
            self._parse_suggestion(item) for item in raw_suggestions if isinstance(item, dict)
        )
        return ICD10SuggestionSet(
            suggestions=suggestions, raw_text=raw_text, output_format=output_format
        )

    def _parse_suggestion(self, item: dict[str, object]) -> ICD10Suggestion:
        return ICD10Suggestion(
            icd10_code=str(item.get("icd10_code", "") or "").strip(),
            diagnosis_name=str(item.get("diagnosis_name", "") or "").strip(),
            confidence_score=self._parse_confidence(item.get("confidence_score")),
            clinical_reasoning=str(item.get("clinical_reasoning", "") or "").strip(),
            supporting_evidence=str(item.get("supporting_evidence", "") or "").strip(),
            flag=self._parse_flag(item.get("flag")),
        )

    def _parse_confidence(self, value: object) -> float | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int | float):
            return float(value)
        return None

    def _parse_flag(self, value: object) -> DiagnosisFlag:
        if isinstance(value, str):
            try:
                return DiagnosisFlag(value.strip().lower())
            except ValueError:
                return DiagnosisFlag.SECONDARY
        return DiagnosisFlag.SECONDARY
