"""`DefaultMedicalReasoningValidator` — the one concrete
`MedicalReasoningValidatorPort` implementation this task ships, per
"VALIDATION — malformed JSON, missing reasoning, duplicate evidence,
invalid confidence values, hallucinated placeholders, inconsistent
recommendations, empty outputs" ("malformed JSON" is
`MedicalReasoningParserPort`'s concern — a result that reaches this
validator already parsed successfully, so only content-level checks
remain here, the same split
`app.modules.differential_diagnosis_ai.infrastructure.validation
.differential_diagnosis_validator.DefaultDifferentialDiagnosisValidator`
documents for itself).

Constructor-injected with `EvidenceAnalysisService` and
`RecommendationReasoningService` — this task's own "Do NOT duplicate
implementations" rule means duplicate-evidence and inconsistent-
recommendation *detection* live once, on those application-layer
services, and this infrastructure-layer validator calls them rather than
re-implementing the same checks (infrastructure depending on application
is the same direction Clean Architecture's dependency rule always
allows — application never depends back on infrastructure).

Reuses `app.shared.infrastructure.text_processing.placeholder_detection
.find_placeholder_marker` (rule: "Reuse... Shared validator... Avoid
duplicate implementations").

Checks run in this order, each a distinct failure mode with its own
domain exception:

1. A fully vacuous result (no summary, no evidence, no risk factors, no
   red flags, no recommendations, no justification) ->
   `EmptyReasoningResponseError`.
2. A blank `clinical_summary`, or a blank `clinical_justification` while
   evidence/risk factors/red flags/recommendations were reported (a
   justification is expected wherever there is something to justify) ->
   `MissingReasoningError`.
3. Any evidence description reported more than once (via
   `EvidenceAnalysisService.find_duplicates`) -> `DuplicateEvidenceError`.
4. Any of the three confidence dimensions that *is* present but outside
   `[0.0, 1.0]` -> `InvalidConfidenceValueError` — `None` is not an
   error here (unlike `app.modules.icd10_ai`'s stricter requirement):
   this module has no ranking step depending on every score being
   populated, so a missing dimension is filled in deterministically by
   `ConfidenceScoringService` during enrichment instead of being
   rejected outright.
5. Any hallucinated placeholder in `clinical_summary`,
   `clinical_justification`, or any evidence/risk-factor/red-flag/
   recommendation text -> `HallucinatedReasoningPlaceholderError`.
6. Any recommendation list (`suggested_next_questions`,
   `suggested_investigations`, `suggested_monitoring`) containing the
   same entry twice (via
   `RecommendationReasoningService.find_duplicate`) ->
   `InconsistentRecommendationsError`.
"""

from app.modules.medical_reasoning_ai.application.ports import MedicalReasoningValidatorPort
from app.modules.medical_reasoning_ai.application.services.evidence_analysis_service import (
    EvidenceAnalysisService,
)
from app.modules.medical_reasoning_ai.application.services.recommendation_reasoning_service import (
    RecommendationReasoningService,
)
from app.modules.medical_reasoning_ai.domain.exceptions import (
    DuplicateEvidenceError,
    EmptyReasoningResponseError,
    HallucinatedReasoningPlaceholderError,
    InconsistentRecommendationsError,
    InvalidConfidenceValueError,
    MissingReasoningError,
)
from app.modules.medical_reasoning_ai.domain.value_objects import MedicalReasoningResult
from app.shared.infrastructure.text_processing.placeholder_detection import (
    find_placeholder_marker,
)

_RECOMMENDATION_LISTS = (
    "suggested_next_questions",
    "suggested_investigations",
    "suggested_monitoring",
)


class DefaultMedicalReasoningValidator(MedicalReasoningValidatorPort):
    def __init__(
        self,
        *,
        evidence_service: EvidenceAnalysisService,
        recommendation_service: RecommendationReasoningService,
    ) -> None:
        self._evidence_service = evidence_service
        self._recommendation_service = recommendation_service

    def validate(self, result: MedicalReasoningResult) -> None:
        if result.is_empty:
            raise EmptyReasoningResponseError()

        self._check_missing_reasoning(result)
        self._check_duplicate_evidence(result)
        self._check_confidence_values(result)
        self._check_hallucinated_placeholders(result)
        self._check_inconsistent_recommendations(result)

    def _check_missing_reasoning(self, result: MedicalReasoningResult) -> None:
        if not result.clinical_summary.strip():
            raise MissingReasoningError("clinical_summary must not be blank")

        has_supporting_content = bool(
            result.evidence
            or result.risk_factors
            or result.red_flags
            or result.suggested_next_questions
            or result.suggested_investigations
            or result.suggested_monitoring
        )
        if has_supporting_content and not result.clinical_justification.strip():
            raise MissingReasoningError(
                "clinical_justification must not be blank when evidence, risks, or "
                "recommendations were reported"
            )

    def _check_duplicate_evidence(self, result: MedicalReasoningResult) -> None:
        duplicates = self._evidence_service.find_duplicates(result.evidence)
        if duplicates:
            raise DuplicateEvidenceError(duplicates[0])

    def _check_confidence_values(self, result: MedicalReasoningResult) -> None:
        dimensions = (
            ("clinical", result.clinical_confidence),
            ("diagnostic", result.diagnostic_confidence),
            ("therapeutic", result.therapeutic_confidence),
        )
        for name, value in dimensions:
            if value is not None and not (0.0 <= value <= 1.0):
                raise InvalidConfidenceValueError(name)

    def _check_hallucinated_placeholders(self, result: MedicalReasoningResult) -> None:
        text_fields = (
            ("clinical_summary", result.clinical_summary),
            ("clinical_justification", result.clinical_justification),
        )
        for field_name, text in text_fields:
            placeholder = find_placeholder_marker(text)
            if placeholder is not None:
                raise HallucinatedReasoningPlaceholderError(field_name, placeholder)

        for item in result.evidence:
            placeholder = find_placeholder_marker(item.description)
            if placeholder is not None:
                raise HallucinatedReasoningPlaceholderError("evidence", placeholder)

        list_fields = (
            ("risk_factors", result.risk_factors),
            ("suggested_next_questions", result.suggested_next_questions),
            ("suggested_investigations", result.suggested_investigations),
            ("suggested_monitoring", result.suggested_monitoring),
        )
        for field_name, items in list_fields:
            for text in items:
                placeholder = find_placeholder_marker(text)
                if placeholder is not None:
                    raise HallucinatedReasoningPlaceholderError(field_name, placeholder)

        for flag in result.red_flags:
            placeholder = find_placeholder_marker(flag.description)
            if placeholder is not None:
                raise HallucinatedReasoningPlaceholderError("red_flags", placeholder)

    def _check_inconsistent_recommendations(self, result: MedicalReasoningResult) -> None:
        for list_name in _RECOMMENDATION_LISTS:
            items: tuple[str, ...] = getattr(result, list_name)
            duplicate = self._recommendation_service.find_duplicate(items)
            if duplicate is not None:
                raise InconsistentRecommendationsError(list_name, duplicate)
