"""`DefaultDrugSafetyAnalysisValidator` — the one concrete
`DrugSafetyAnalysisValidatorPort` implementation this task ships, per
this task's own "unknown medications, malformed JSON, hallucinated
interactions, invalid confidence, missing required evidence" VALIDATION
categories ("malformed JSON" is `DrugSafetyAnalysisParserPort`'s
concern, and "empty medication lists"/"duplicate medications" are
`domain/value_objects.py`'s own `__post_init__` concern on the
caller-supplied *input* — a result that reaches this validator already
parsed successfully, so only content-level checks on the AI's own
*output* remain here, the same split every prior AI module's own
validator documents for itself).

`validate` takes `input_dto` in addition to `result` — unlike every
prior AI module's own validator — because "unknown medications" can only
be checked against the medications the caller actually supplied: it
means the AI's response references a drug name that never appeared in
`current_medications`/`new_prescription` (a drug-specific hallucination
worth its own dedicated category), not a caller-supplied name this
module fails to recognize from an external drug dictionary this module
does not maintain (see `domain/exceptions.py`'s own module docstring for
the full reasoning).

Checks run in this order, each a distinct failure mode with its own
domain exception:

1. Any `SafetyIssue.involved_medications` entry that does not
   case-insensitively match (by substring, tolerating dose/strength
   suffixes the AI may add) any `drug_name`/`generic_name`/`brand_name`
   the caller actually supplied -> `UnknownMedicationError`.
2. `confidence_score` present but outside `[0.0, 1.0]` ->
   `InvalidDrugInteractionConfidenceValueError`. `None` is not an error
   here: this module's confidence is always deterministically filled in
   by `MedicalReasoningAIPort.score_confidence` during enrichment (see
   `application/use_cases/analyze_medication_safety.py`), so a missing
   AI-reported value is expected, not invalid.
3. Any interaction whose `severity` is `SafetySeverity.MAJOR` or
   `CONTRAINDICATED` but whose `evidence_level` is `None` ->
   `MissingInteractionEvidenceError` — a severe safety claim without any
   supporting evidence grade is exactly what this task's own "missing
   required evidence" category exists to catch.
4. Any hallucinated placeholder in `safety_summary`,
   `clinical_reasoning`, or any interaction/contraindication/warning/
   recommendation text -> `HallucinatedInteractionError`.
"""

from app.modules.drug_interaction_ai.application.ports import DrugSafetyAnalysisValidatorPort
from app.modules.drug_interaction_ai.domain.enums import SafetySeverity
from app.modules.drug_interaction_ai.domain.exceptions import (
    HallucinatedInteractionError,
    InvalidDrugInteractionConfidenceValueError,
    MissingInteractionEvidenceError,
    UnknownMedicationError,
)
from app.modules.drug_interaction_ai.domain.value_objects import (
    DrugInteractionAnalysisInput,
    DrugInteractionAnalysisResult,
    MedicationEntry,
)
from app.shared.infrastructure.text_processing.placeholder_detection import (
    find_placeholder_marker,
)

_EVIDENCE_REQUIRED_SEVERITIES = (SafetySeverity.MAJOR, SafetySeverity.CONTRAINDICATED)


class DefaultDrugSafetyAnalysisValidator(DrugSafetyAnalysisValidatorPort):
    def validate(
        self, result: DrugInteractionAnalysisResult, input_dto: DrugInteractionAnalysisInput
    ) -> None:
        self._check_unknown_medications(result, input_dto)
        self._check_confidence_value(result)
        self._check_missing_evidence(result)
        self._check_hallucinated_placeholders(result)

    def _known_medication_names(self, input_dto: DrugInteractionAnalysisInput) -> set[str]:
        names: set[str] = set()
        medications: list[MedicationEntry] = list(input_dto.current_medications)
        if input_dto.new_prescription is not None:
            medications.append(input_dto.new_prescription)
        for medication in medications:
            names.add(medication.drug_name.strip().lower())
            if medication.generic_name:
                names.add(medication.generic_name.strip().lower())
            if medication.brand_name:
                names.add(medication.brand_name.strip().lower())
        return names

    def _check_unknown_medications(
        self, result: DrugInteractionAnalysisResult, input_dto: DrugInteractionAnalysisInput
    ) -> None:
        known_names = self._known_medication_names(input_dto)
        for issue in result.interactions:
            for medication_name in issue.involved_medications:
                normalized = medication_name.strip().lower()
                if not any(normalized in known or known in normalized for known in known_names):
                    raise UnknownMedicationError(medication_name)

    def _check_confidence_value(self, result: DrugInteractionAnalysisResult) -> None:
        if result.confidence_score is not None and not (0.0 <= result.confidence_score <= 1.0):
            raise InvalidDrugInteractionConfidenceValueError()

    def _check_missing_evidence(self, result: DrugInteractionAnalysisResult) -> None:
        for issue in result.interactions:
            if issue.severity in _EVIDENCE_REQUIRED_SEVERITIES and issue.evidence_level is None:
                raise MissingInteractionEvidenceError(issue.description)

    def _check_hallucinated_placeholders(self, result: DrugInteractionAnalysisResult) -> None:
        text_fields = (
            ("safety_summary", result.safety_summary),
            ("clinical_reasoning", result.clinical_reasoning),
        )
        for field_name, text in text_fields:
            placeholder = find_placeholder_marker(text)
            if placeholder is not None:
                raise HallucinatedInteractionError(field_name, placeholder)

        for issue in result.interactions:
            for issue_text in (issue.description, issue.mechanism, issue.clinical_significance):
                if issue_text is None:
                    continue
                placeholder = find_placeholder_marker(issue_text)
                if placeholder is not None:
                    raise HallucinatedInteractionError("interactions", placeholder)

        list_fields = (
            ("contraindications", result.contraindications),
            ("warnings", result.warnings),
            ("monitoring_recommendations", result.monitoring_recommendations),
            ("dose_adjustment_suggestions", result.dose_adjustment_suggestions),
            ("alternative_medication_suggestions", result.alternative_medication_suggestions),
            ("patient_counseling_points", result.patient_counseling_points),
        )
        for field_name, items in list_fields:
            for text in items:
                placeholder = find_placeholder_marker(text)
                if placeholder is not None:
                    raise HallucinatedInteractionError(field_name, placeholder)
