"""`DefaultDrugSafetyAnalysisParser` — the one concrete
`DrugSafetyAnalysisParserPort` implementation this task ships, per this
task's own PARSING section ("Support: JSON, Markdown, Plain text").

Reuses `app.shared.infrastructure.text_processing.json_extraction
.extract_json_object` for the mechanical fence-stripping/`json.loads`
work (rule: "Reuse... Shared parser... Avoid duplicate implementations")
— the AI is always prompted for one fixed-shape JSON object (the
`_JSON_CONTRACT` in `infrastructure/prompts/templates.py`) regardless of
`output_format`; markdown/plain-text *rendering* is a separate, later
concern (`application/services/drug_safety_report_renderer
.DrugSafetyReportRenderer.render`), the same "generation produces
structure; rendering produces presentation" split every prior AI
module's own parser establishes for itself.

Missing/malformed fields become an empty string/tuple, `None`
(`confidence_score`, `evidence_level`, `mechanism`,
`clinical_significance`), or a lenient default (`severity` defaults to
`SafetySeverity.MODERATE`; an unparseable `category` defaults to
`SafetyIssueCategory.DRUG_DRUG_INTERACTION`, the first and most common
of this task's own eighteen DETECT categories) — never a parse failure.
"Unknown medications"/"hallucinated interactions"/"invalid confidence"/
"missing required evidence" are `DrugSafetyAnalysisValidatorPort`'s job
(per this task's own VALIDATION section), so this parser stays purely
mechanical: a top-level JSON object that isn't the expected shape, or
isn't parseable JSON at all, is the only thing that fails parsing
itself.
"""

from app.modules.drug_interaction_ai.application.ports import DrugSafetyAnalysisParserPort
from app.modules.drug_interaction_ai.domain.enums import (
    DrugInteractionOutputFormat,
    EvidenceLevel,
    SafetyIssueCategory,
    SafetySeverity,
)
from app.modules.drug_interaction_ai.domain.exceptions import (
    InvalidDrugInteractionResponseFormatError,
)
from app.modules.drug_interaction_ai.domain.value_objects import (
    DrugInteractionAnalysisResult,
    SafetyIssue,
)
from app.shared.infrastructure.text_processing.json_extraction import extract_json_object


class DefaultDrugSafetyAnalysisParser(DrugSafetyAnalysisParserPort):
    def parse(
        self, raw_text: str, *, output_format: DrugInteractionOutputFormat
    ) -> DrugInteractionAnalysisResult:
        try:
            payload = extract_json_object(raw_text)
        except ValueError as exc:
            raise InvalidDrugInteractionResponseFormatError(str(exc)) from exc

        raw_interactions = payload.get("interactions")
        interactions = (
            tuple(self._parse_issue(item) for item in raw_interactions if isinstance(item, dict))
            if isinstance(raw_interactions, list)
            else ()
        )

        return DrugInteractionAnalysisResult(
            safety_summary=str(payload.get("safety_summary", "") or "").strip(),
            interactions=interactions,
            contraindications=self._parse_string_list(payload.get("contraindications")),
            warnings=self._parse_string_list(payload.get("warnings")),
            monitoring_recommendations=self._parse_string_list(
                payload.get("monitoring_recommendations")
            ),
            dose_adjustment_suggestions=self._parse_string_list(
                payload.get("dose_adjustment_suggestions")
            ),
            alternative_medication_suggestions=self._parse_string_list(
                payload.get("alternative_medication_suggestions")
            ),
            patient_counseling_points=self._parse_string_list(
                payload.get("patient_counseling_points")
            ),
            clinical_reasoning=str(payload.get("clinical_reasoning", "") or "").strip(),
            confidence_score=self._parse_confidence(payload.get("confidence_score")),
            raw_text=raw_text,
            output_format=output_format,
        )

    def _parse_issue(self, item: dict[str, object]) -> SafetyIssue:
        return SafetyIssue(
            category=self._parse_category(item.get("category")),
            description=str(item.get("description", "") or "").strip(),
            severity=self._parse_severity(item.get("severity")),
            mechanism=self._parse_optional_str(item.get("mechanism")),
            clinical_significance=self._parse_optional_str(item.get("clinical_significance")),
            evidence_level=self._parse_evidence_level(item.get("evidence_level")),
            involved_medications=self._parse_string_list(item.get("involved_medications")),
        )

    def _parse_optional_str(self, value: object) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    def _parse_category(self, value: object) -> SafetyIssueCategory:
        if isinstance(value, str):
            try:
                return SafetyIssueCategory(value.strip().lower())
            except ValueError:
                return SafetyIssueCategory.DRUG_DRUG_INTERACTION
        return SafetyIssueCategory.DRUG_DRUG_INTERACTION

    def _parse_severity(self, value: object) -> SafetySeverity:
        if isinstance(value, str):
            try:
                return SafetySeverity(value.strip().lower())
            except ValueError:
                return SafetySeverity.MODERATE
        return SafetySeverity.MODERATE

    def _parse_evidence_level(self, value: object) -> EvidenceLevel | None:
        if isinstance(value, str):
            try:
                return EvidenceLevel(value.strip().lower())
            except ValueError:
                return None
        return None

    def _parse_confidence(self, value: object) -> float | None:
        """Deliberately **not** clamped to `[0.0, 1.0]` here — this
        task's own VALIDATION section explicitly names "invalid
        confidence" as its own category, so an out-of-range AI-reported
        value is passed through as-is and left for
        `DrugSafetyAnalysisValidatorPort` to reject
        (`InvalidDrugInteractionConfidenceValueError`), the same
        "parsing stays purely mechanical; content-level checks belong to
        the validator" split this parser's own module docstring
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
