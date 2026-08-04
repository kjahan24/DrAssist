"""`DefaultMedicalReasoningParser` — the one concrete
`MedicalReasoningParserPort` implementation this task ships, per this
task's own OUTPUT specification.

Reuses `app.shared.infrastructure.text_processing.json_extraction
.extract_json_object` for the mechanical fence-stripping/`json.loads`
work (rule: "Reuse... Shared parser... Avoid duplicate implementations"
— see that function's own docstring for why it lives in the shared
kernel rather than a further copy of the same regex).

The AI is always prompted for a single fixed-shape JSON object (the
`_JSON_CONTRACT` in `infrastructure/prompts/templates.py`) regardless of
`output_format`; markdown/text are handled at render time instead
(`application/services/clinical_summary_service.ClinicalSummaryService
.render`), the same "generation produces structure; rendering produces
presentation" split `app.modules.differential_diagnosis_ai.infrastructure
.parsing.differential_diagnosis_parser` uses for itself.

Missing/malformed fields become an empty string/tuple, `None`
(confidence values), or a lenient default (`polarity` defaults to
`EvidencePolarity.SUPPORTING`; `priority` defaults to
`RedFlagPriority.MODERATE`) — never a parse failure. "Missing reasoning"/
"duplicate evidence"/"invalid confidence values"/"hallucinated
placeholders"/"inconsistent recommendations"/"empty outputs" are
`MedicalReasoningValidatorPort`'s job (per this task's own VALIDATION
section), so this parser stays purely mechanical: a top-level JSON
object that isn't the expected shape, or isn't parseable JSON at all, is
the only thing that fails parsing itself.
"""

from app.modules.medical_reasoning_ai.application.ports import MedicalReasoningParserPort
from app.modules.medical_reasoning_ai.domain.enums import (
    EvidencePolarity,
    MedicalReasoningOutputFormat,
    RedFlagPriority,
)
from app.modules.medical_reasoning_ai.domain.exceptions import (
    InvalidMedicalReasoningResponseFormatError,
)
from app.modules.medical_reasoning_ai.domain.value_objects import (
    EvidenceItem,
    MedicalReasoningResult,
    RedFlag,
)
from app.shared.infrastructure.text_processing.json_extraction import extract_json_object


class DefaultMedicalReasoningParser(MedicalReasoningParserPort):
    def parse(
        self, raw_text: str, *, output_format: MedicalReasoningOutputFormat
    ) -> MedicalReasoningResult:
        try:
            payload = extract_json_object(raw_text)
        except ValueError as exc:
            raise InvalidMedicalReasoningResponseFormatError(str(exc)) from exc

        raw_evidence = payload.get("evidence")
        evidence = (
            tuple(
                self._parse_evidence_item(item) for item in raw_evidence if isinstance(item, dict)
            )
            if isinstance(raw_evidence, list)
            else ()
        )

        raw_red_flags = payload.get("red_flags")
        red_flags = (
            tuple(self._parse_red_flag(item) for item in raw_red_flags if isinstance(item, dict))
            if isinstance(raw_red_flags, list)
            else ()
        )

        return MedicalReasoningResult(
            clinical_summary=str(payload.get("clinical_summary", "") or "").strip(),
            evidence=evidence,
            missing_information=self._parse_string_list(payload.get("missing_information")),
            clinical_confidence=self._parse_confidence(payload.get("clinical_confidence")),
            diagnostic_confidence=self._parse_confidence(payload.get("diagnostic_confidence")),
            therapeutic_confidence=self._parse_confidence(payload.get("therapeutic_confidence")),
            risk_factors=self._parse_string_list(payload.get("risk_factors")),
            red_flags=red_flags,
            suggested_next_questions=self._parse_string_list(
                payload.get("suggested_next_questions")
            ),
            suggested_investigations=self._parse_string_list(
                payload.get("suggested_investigations")
            ),
            suggested_monitoring=self._parse_string_list(payload.get("suggested_monitoring")),
            clinical_justification=str(payload.get("clinical_justification", "") or "").strip(),
            raw_text=raw_text,
            output_format=output_format,
        )

    def _parse_evidence_item(self, item: dict[str, object]) -> EvidenceItem:
        return EvidenceItem(
            description=str(item.get("description", "") or "").strip(),
            weight=self._parse_weight(item.get("weight")),
            polarity=self._parse_polarity(item.get("polarity")),
        )

    def _parse_weight(self, value: object) -> float:
        if isinstance(value, bool):
            return 0.5
        if isinstance(value, int | float):
            return max(0.0, min(1.0, float(value)))
        return 0.5

    def _parse_polarity(self, value: object) -> EvidencePolarity:
        if isinstance(value, str):
            try:
                return EvidencePolarity(value.strip().lower())
            except ValueError:
                return EvidencePolarity.SUPPORTING
        return EvidencePolarity.SUPPORTING

    def _parse_red_flag(self, item: dict[str, object]) -> RedFlag:
        return RedFlag(
            description=str(item.get("description", "") or "").strip(),
            priority=self._parse_priority(item.get("priority")),
        )

    def _parse_priority(self, value: object) -> RedFlagPriority:
        if isinstance(value, str):
            try:
                return RedFlagPriority(value.strip().lower())
            except ValueError:
                return RedFlagPriority.MODERATE
        return RedFlagPriority.MODERATE

    def _parse_confidence(self, value: object) -> float | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int | float):
            return float(value)
        return None

    def _parse_string_list(self, value: object) -> tuple[str, ...]:
        if not isinstance(value, list):
            return ()
        return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
