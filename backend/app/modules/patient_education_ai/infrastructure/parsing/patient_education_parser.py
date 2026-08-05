"""`DefaultPatientEducationAnalysisParser` — the one concrete
`PatientEducationAnalysisParserPort` implementation this task ships, per
this task's own OUTPUT section ("Support: JSON, Markdown, Plain text").

Reuses `app.shared.infrastructure.text_processing.json_extraction
.extract_json_object` for the mechanical fence-stripping/`json.loads`
work (rule: "Reuse... Shared parser... Avoid duplicate implementations")
— the AI is always prompted for one fixed-shape JSON object (the
`_JSON_CONTRACT` in `infrastructure/prompts/templates.py`) regardless of
`output_format`; markdown/plain-text *rendering* is a separate, later
concern (`application/services/patient_education_report_renderer
.PatientEducationReportRenderer.render`), the same "generation produces
structure; rendering produces presentation" split every prior AI
module's own parser establishes for itself.

Missing/malformed fields become an empty string/tuple or `None`
(`confidence_score`) — never a parse failure. "Hallucinated
recommendations"/"unsafe instructions"/"invalid confidence" are
`PatientEducationAnalysisValidatorPort`'s job (per this task's own
VALIDATION section), so this parser stays purely mechanical: a
top-level JSON object that isn't the expected shape, or isn't parseable
JSON at all, is the only thing that fails parsing itself.
"""

from app.modules.patient_education_ai.application.ports import (
    PatientEducationAnalysisParserPort,
)
from app.modules.patient_education_ai.domain.enums import PatientEducationOutputFormat
from app.modules.patient_education_ai.domain.exceptions import (
    InvalidPatientEducationResponseFormatError,
)
from app.modules.patient_education_ai.domain.value_objects import PatientEducationResult
from app.shared.infrastructure.text_processing.json_extraction import extract_json_object


class DefaultPatientEducationAnalysisParser(PatientEducationAnalysisParserPort):
    def parse(
        self, raw_text: str, *, output_format: PatientEducationOutputFormat
    ) -> PatientEducationResult:
        try:
            payload = extract_json_object(raw_text)
        except ValueError as exc:
            raise InvalidPatientEducationResponseFormatError(str(exc)) from exc

        return PatientEducationResult(
            patient_summary=str(payload.get("patient_summary", "") or "").strip(),
            diagnosis_explanation=str(payload.get("diagnosis_explanation", "") or "").strip(),
            medication_instructions=self._parse_string_list(payload.get("medication_instructions")),
            home_care_plan=self._parse_string_list(payload.get("home_care_plan")),
            lifestyle_advice=self._parse_string_list(payload.get("lifestyle_advice")),
            diet_advice=self._parse_string_list(payload.get("diet_advice")),
            exercise_advice=self._parse_string_list(payload.get("exercise_advice")),
            warning_signs=self._parse_string_list(payload.get("warning_signs")),
            emergency_instructions=self._parse_string_list(payload.get("emergency_instructions")),
            follow_up_plan=self._parse_string_list(payload.get("follow_up_plan")),
            patient_checklist=self._parse_string_list(payload.get("patient_checklist")),
            confidence_score=self._parse_confidence(payload.get("confidence_score")),
            raw_text=raw_text,
            output_format=output_format,
        )

    def _parse_confidence(self, value: object) -> float | None:
        """Deliberately **not** clamped to `[0.0, 1.0]` here — this
        task's own VALIDATION section explicitly names "invalid
        confidence" as its own category, so an out-of-range AI-reported
        value is passed through as-is and left for
        `PatientEducationAnalysisValidatorPort` to reject
        (`InvalidPatientEducationConfidenceValueError`), the same
        "parsing stays purely mechanical; content-level checks belong
        to the validator" split this parser's own module docstring
        documents."""
        if isinstance(value, bool):
            return None
        if isinstance(value, int | float):
            return float(value)
        return None

    def _parse_string_list(self, value: object) -> tuple[str, ...]:
        if not isinstance(value, list):
            return ()
        return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
