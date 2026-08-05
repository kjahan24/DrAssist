"""`DefaultPathologyInterpretationValidator` — the one concrete
`PathologyInterpretationValidatorPort` implementation this task ships,
per this task's own "duplicated findings, malformed JSON, hallucinated
findings, inconsistent conclusions, invalid confidence values"
VALIDATION categories ("malformed JSON" is
`PathologyInterpretationParserPort`'s concern, and "empty reports"/
"malformed reports" are `domain/value_objects.py`'s own `__post_init__`
concern on the caller-supplied *input* — a result that reaches this
validator already parsed successfully, so only content-level checks on
the AI's own *output* remain here, the same split every prior AI
module's own validator documents for itself).

Constructor-injected with `ClinicalCorrelationService` — this task's own
"Do NOT duplicate implementations" rule means duplicate-conclusion
*detection* lives once, on that application-layer service, and this
infrastructure-layer validator calls it rather than re-implementing the
same check (infrastructure depending on application is the same
direction Clean Architecture's dependency rule always allows).
Duplicate-*finding* detection has no equally natural owner among this
task's own four named application services (none of
`FindingExtractionService`/`MalignancyAssessmentService`/
`ClinicalCorrelationService`/`PathologySummaryService` is "finding list
hygiene"), so that one check is implemented directly here instead of
forcing an artificial service dependency onto an unrelated service.

Reuses `app.shared.infrastructure.text_processing.placeholder_detection
.find_placeholder_marker` (rule: "Reuse... Shared validator... Avoid
duplicate implementations").

Checks run in this order, each a distinct failure mode with its own
domain exception:

1. Any microscopic finding description reported more than once ->
   `DuplicatePathologyFindingError`.
2. `confidence_score` present but outside `[0.0, 1.0]` ->
   `InvalidPathologyConfidenceValueError`. `None` is not an error here:
   this module's confidence is always deterministically filled in by
   `MedicalReasoningAIPort.score_confidence` during enrichment (see
   `application/use_cases/interpret_pathology_report.py`), so a missing
   AI-reported value is expected, not invalid.
3. Any hallucinated placeholder in `pathology_summary`,
   `final_impression`, `clinical_significance`, `clinical_reasoning`, or
   any finding/conclusion/red-flag text ->
   `HallucinatedPathologyFindingError`.
4. Any conclusion list (`correlation_recommendations`,
   `suggested_follow_up`, `suggested_specialist_referral`) containing
   the same entry twice (via `ClinicalCorrelationService.find_duplicate`)
   -> `InconsistentPathologyConclusionsError`.
"""

from app.modules.pathology_interpretation_ai.application.ports import (
    PathologyInterpretationValidatorPort,
)
from app.modules.pathology_interpretation_ai.application.services.clinical_correlation_service import (  # noqa: E501
    ClinicalCorrelationService,
)
from app.modules.pathology_interpretation_ai.domain.exceptions import (
    DuplicatePathologyFindingError,
    HallucinatedPathologyFindingError,
    InconsistentPathologyConclusionsError,
    InvalidPathologyConfidenceValueError,
)
from app.modules.pathology_interpretation_ai.domain.value_objects import (
    PathologyInterpretationResult,
)
from app.shared.infrastructure.text_processing.placeholder_detection import (
    find_placeholder_marker,
)

_CONCLUSION_LISTS = (
    "correlation_recommendations",
    "suggested_follow_up",
    "suggested_specialist_referral",
)


class DefaultPathologyInterpretationValidator(PathologyInterpretationValidatorPort):
    def __init__(self, *, correlation_service: ClinicalCorrelationService) -> None:
        self._correlation_service = correlation_service

    def validate(self, result: PathologyInterpretationResult) -> None:
        self._check_duplicate_findings(result)
        self._check_confidence_value(result)
        self._check_hallucinated_placeholders(result)
        self._check_inconsistent_conclusions(result)

    def _check_duplicate_findings(self, result: PathologyInterpretationResult) -> None:
        seen: set[str] = set()
        for finding in result.microscopic_findings:
            normalized = finding.description.strip().lower()
            if not normalized:
                continue
            if normalized in seen:
                raise DuplicatePathologyFindingError(finding.description)
            seen.add(normalized)

    def _check_confidence_value(self, result: PathologyInterpretationResult) -> None:
        if result.confidence_score is not None and not (0.0 <= result.confidence_score <= 1.0):
            raise InvalidPathologyConfidenceValueError()

    def _check_hallucinated_placeholders(self, result: PathologyInterpretationResult) -> None:
        text_fields = (
            ("pathology_summary", result.pathology_summary),
            ("final_impression", result.final_impression),
            ("clinical_significance", result.clinical_significance),
            ("clinical_reasoning", result.clinical_reasoning),
        )
        for field_name, text in text_fields:
            placeholder = find_placeholder_marker(text)
            if placeholder is not None:
                raise HallucinatedPathologyFindingError(field_name, placeholder)

        for finding in result.microscopic_findings:
            placeholder = find_placeholder_marker(finding.description)
            if placeholder is not None:
                raise HallucinatedPathologyFindingError("microscopic_findings", placeholder)

        list_fields = (
            ("key_findings", result.key_findings),
            ("correlation_recommendations", result.correlation_recommendations),
            ("suggested_follow_up", result.suggested_follow_up),
            ("suggested_specialist_referral", result.suggested_specialist_referral),
            ("red_flag_warnings", result.red_flag_warnings),
        )
        for field_name, items in list_fields:
            for text in items:
                placeholder = find_placeholder_marker(text)
                if placeholder is not None:
                    raise HallucinatedPathologyFindingError(field_name, placeholder)

    def _check_inconsistent_conclusions(self, result: PathologyInterpretationResult) -> None:
        for list_name in _CONCLUSION_LISTS:
            items: tuple[str, ...] = getattr(result, list_name)
            duplicate = self._correlation_service.find_duplicate(items)
            if duplicate is not None:
                raise InconsistentPathologyConclusionsError(list_name, duplicate)
