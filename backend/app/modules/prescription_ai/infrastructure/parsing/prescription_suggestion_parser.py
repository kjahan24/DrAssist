"""`DefaultPrescriptionSuggestionParser` — the one concrete
`PrescriptionSuggestionParserPort` implementation this task ships, per
this task's own OUTPUT specification.

Reuses `app.shared.infrastructure.text_processing.json_extraction
.extract_json_object` for the mechanical fence-stripping/`json.loads`
work (rule: "Reuse... Shared parser framework... Avoid duplicate
implementations" — see that function's own docstring for why it lives in
the shared kernel rather than a further copy of the same regex).

The AI is always prompted for a single fixed-shape JSON object —
`"medications"`, `"safety_findings"`, `"monitoring_recommendations"`,
`"follow_up_recommendations"` (the `_JSON_CONTRACT` in
`infrastructure/prompts/templates.py`) — regardless of `output_format`;
markdown/text are handled at render time instead
(`application/services/prescription_suggestion_renderer.py`), the same
"generation produces structure; rendering produces presentation" split
`app.modules.icd10_ai.infrastructure.parsing.icd10_suggestion_parser`
uses for itself.

Missing/malformed fields *within* an individual medication or safety
finding become an empty string, `None`, or a lenient default (`route`
defaults to `AdministrationRoute.OTHER`; `is_prn` defaults to `False`) —
never a parse failure. "Missing dosage"/"missing frequency"/"missing
duration"/"invalid medication structure"/"duplicated medications"/
"hallucinated medications" are `PrescriptionSuggestionValidatorPort`'s
job (per this task's own VALIDATION section), so this parser stays
purely mechanical: a top-level JSON object that isn't the expected shape,
or isn't parseable JSON at all, is the only thing that fails parsing
itself. Safety findings whose `category` does not match one of the nine
recognized categories are skipped (not a parse failure) — there is no
safe "default" category to fall back to, unlike `flag`/`route`.
"""

from app.modules.prescription_ai.application.ports import PrescriptionSuggestionParserPort
from app.modules.prescription_ai.domain.enums import (
    AdministrationRoute,
    PrescriptionOutputFormat,
    SafetyFindingCategory,
    SafetySeverity,
)
from app.modules.prescription_ai.domain.exceptions import InvalidPrescriptionResponseFormatError
from app.modules.prescription_ai.domain.value_objects import (
    MedicationSafetyFinding,
    MedicationSuggestion,
    PrescriptionSuggestionSet,
)
from app.shared.infrastructure.text_processing.json_extraction import extract_json_object


class DefaultPrescriptionSuggestionParser(PrescriptionSuggestionParserPort):
    def parse(
        self, raw_text: str, *, output_format: PrescriptionOutputFormat
    ) -> PrescriptionSuggestionSet:
        try:
            payload = extract_json_object(raw_text)
        except ValueError as exc:
            raise InvalidPrescriptionResponseFormatError(str(exc)) from exc

        raw_medications = payload.get("medications")
        if not isinstance(raw_medications, list):
            raise InvalidPrescriptionResponseFormatError(
                'expected a "medications" array in the AI\'s JSON response'
            )

        medications = tuple(
            self._parse_medication(item) for item in raw_medications if isinstance(item, dict)
        )

        raw_findings = payload.get("safety_findings")
        findings = (
            tuple(
                finding
                for item in raw_findings
                if isinstance(item, dict)
                and (finding := self._parse_safety_finding(item)) is not None
            )
            if isinstance(raw_findings, list)
            else ()
        )

        return PrescriptionSuggestionSet(
            medications=medications,
            safety_findings=findings,
            monitoring_recommendations=self._parse_string_list(
                payload.get("monitoring_recommendations")
            ),
            follow_up_recommendations=self._parse_string_list(
                payload.get("follow_up_recommendations")
            ),
            raw_text=raw_text,
            output_format=output_format,
        )

    def _parse_medication(self, item: dict[str, object]) -> MedicationSuggestion:
        brand_name_raw = item.get("brand_name")
        brand_name = (
            brand_name_raw.strip()
            if isinstance(brand_name_raw, str) and brand_name_raw.strip()
            else None
        )
        return MedicationSuggestion(
            generic_name=str(item.get("generic_name", "") or "").strip(),
            brand_name=brand_name,
            strength=str(item.get("strength", "") or "").strip(),
            dosage=str(item.get("dosage", "") or "").strip(),
            route=self._parse_route(item.get("route")),
            frequency=str(item.get("frequency", "") or "").strip(),
            duration=str(item.get("duration", "") or "").strip(),
            quantity=str(item.get("quantity", "") or "").strip(),
            is_prn=item.get("is_prn") is True,
            clinical_indication=str(item.get("clinical_indication", "") or "").strip(),
            monitoring_advice=str(item.get("monitoring_advice", "") or "").strip(),
            patient_instructions=str(item.get("patient_instructions", "") or "").strip(),
            confidence_score=self._parse_confidence(item.get("confidence_score")),
            clinical_reasoning=str(item.get("clinical_reasoning", "") or "").strip(),
        )

    def _parse_route(self, value: object) -> AdministrationRoute:
        if isinstance(value, str):
            try:
                return AdministrationRoute(value.strip().lower())
            except ValueError:
                return AdministrationRoute.OTHER
        return AdministrationRoute.OTHER

    def _parse_confidence(self, value: object) -> float | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int | float):
            return float(value)
        return None

    def _parse_safety_finding(self, item: dict[str, object]) -> MedicationSafetyFinding | None:
        category = self._parse_category(item.get("category"))
        if category is None:
            return None
        affected_raw = item.get("affected_medications")
        affected = self._parse_string_list(affected_raw)
        return MedicationSafetyFinding(
            category=category,
            severity=self._parse_severity(item.get("severity")),
            description=str(item.get("description", "") or "").strip(),
            affected_medications=affected,
        )

    def _parse_category(self, value: object) -> SafetyFindingCategory | None:
        if isinstance(value, str):
            try:
                return SafetyFindingCategory(value.strip().lower())
            except ValueError:
                return None
        return None

    def _parse_severity(self, value: object) -> SafetySeverity:
        if isinstance(value, str):
            try:
                return SafetySeverity(value.strip().lower())
            except ValueError:
                return SafetySeverity.MODERATE
        return SafetySeverity.MODERATE

    def _parse_string_list(self, value: object) -> tuple[str, ...]:
        if not isinstance(value, list):
            return ()
        return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
