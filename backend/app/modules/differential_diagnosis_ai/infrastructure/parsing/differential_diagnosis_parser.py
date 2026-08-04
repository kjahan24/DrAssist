"""`DefaultDifferentialDiagnosisParser` — the one concrete
`DifferentialDiagnosisParserPort` implementation this task ships, per
this task's own OUTPUT specification.

Reuses `app.shared.infrastructure.text_processing.json_extraction
.extract_json_object` for the mechanical fence-stripping/`json.loads`
work (rule: "Reuse... Shared parser framework... Avoid duplicate
implementations" — see that function's own docstring for why it lives in
the shared kernel rather than a further copy of the same regex).

The AI is always prompted for a single fixed-shape JSON object —
`"candidates"`, `"serious_diagnoses_not_to_miss"`,
`"suggested_investigations"`, `"suggested_referrals"` (the
`_JSON_CONTRACT` in `infrastructure/prompts/templates.py`) — regardless
of `output_format`; markdown/text are handled at render time instead
(`application/services/differential_diagnosis_renderer.py`), the same
"generation produces structure; rendering produces presentation" split
`app.modules.prescription_ai.infrastructure.parsing
.prescription_suggestion_parser` uses for itself.

Missing/malformed fields *within* an individual candidate become an
empty string/tuple, `None` (confidence score, ICD-10 code), or a lenient
default (`urgency_level` defaults to `UrgencyLevel.ROUTINE` — never a
parse failure; the deterministic minimum-urgency enrichment in
`ClinicalReasoningService.upgrade_urgency_levels` runs *after*
validation and will raise it if red flags are present regardless of
this default). "Invalid confidence scores"/"duplicate diagnoses"/
"hallucinated diagnoses"/"invalid ranking"/"inconsistent reasoning" are
`DifferentialDiagnosisValidatorPort`'s job (per this task's own
VALIDATION section), so this parser stays purely mechanical: a top-level
JSON object that isn't the expected shape, or isn't parseable JSON at
all, is the only thing that fails parsing itself.
"""

from app.modules.differential_diagnosis_ai.application.ports import DifferentialDiagnosisParserPort
from app.modules.differential_diagnosis_ai.domain.enums import (
    DifferentialOutputFormat,
    UrgencyLevel,
)
from app.modules.differential_diagnosis_ai.domain.exceptions import (
    InvalidDifferentialResponseFormatError,
)
from app.modules.differential_diagnosis_ai.domain.value_objects import (
    DifferentialDiagnosisCandidate,
    DifferentialDiagnosisResult,
)
from app.shared.infrastructure.text_processing.json_extraction import extract_json_object


class DefaultDifferentialDiagnosisParser(DifferentialDiagnosisParserPort):
    def parse(
        self, raw_text: str, *, output_format: DifferentialOutputFormat
    ) -> DifferentialDiagnosisResult:
        try:
            payload = extract_json_object(raw_text)
        except ValueError as exc:
            raise InvalidDifferentialResponseFormatError(str(exc)) from exc

        raw_candidates = payload.get("candidates")
        if not isinstance(raw_candidates, list):
            raise InvalidDifferentialResponseFormatError(
                'expected a "candidates" array in the AI\'s JSON response'
            )

        candidates = tuple(
            self._parse_candidate(item) for item in raw_candidates if isinstance(item, dict)
        )

        return DifferentialDiagnosisResult(
            candidates=candidates,
            serious_diagnoses_not_to_miss=self._parse_string_list(
                payload.get("serious_diagnoses_not_to_miss")
            ),
            suggested_investigations=self._parse_string_list(
                payload.get("suggested_investigations")
            ),
            suggested_referrals=self._parse_string_list(payload.get("suggested_referrals")),
            raw_text=raw_text,
            output_format=output_format,
        )

    def _parse_candidate(self, item: dict[str, object]) -> DifferentialDiagnosisCandidate:
        icd10_code_raw = item.get("icd10_code")
        icd10_code = (
            icd10_code_raw.strip()
            if isinstance(icd10_code_raw, str) and icd10_code_raw.strip()
            else None
        )
        return DifferentialDiagnosisCandidate(
            disease_name=str(item.get("disease_name", "") or "").strip(),
            icd10_code=icd10_code,
            confidence_score=self._parse_confidence(item.get("confidence_score")),
            clinical_reasoning=str(item.get("clinical_reasoning", "") or "").strip(),
            supporting_findings=self._parse_string_list(item.get("supporting_findings")),
            findings_against=self._parse_string_list(item.get("findings_against")),
            recommended_next_tests=self._parse_string_list(item.get("recommended_next_tests")),
            red_flag_indicators=self._parse_string_list(item.get("red_flag_indicators")),
            urgency_level=self._parse_urgency(item.get("urgency_level")),
        )

    def _parse_confidence(self, value: object) -> float | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int | float):
            return float(value)
        return None

    def _parse_urgency(self, value: object) -> UrgencyLevel:
        if isinstance(value, str):
            try:
                return UrgencyLevel(value.strip().lower())
            except ValueError:
                return UrgencyLevel.ROUTINE
        return UrgencyLevel.ROUTINE

    def _parse_string_list(self, value: object) -> tuple[str, ...]:
        if not isinstance(value, list):
            return ()
        return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
