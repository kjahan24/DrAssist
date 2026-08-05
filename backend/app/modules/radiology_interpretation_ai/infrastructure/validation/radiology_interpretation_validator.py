"""`DefaultRadiologyInterpretationValidator` — the one concrete
`RadiologyInterpretationValidatorPort` implementation this task ships,
per this task's own "duplicated findings, malformed JSON, hallucinated
findings, inconsistent recommendations, invalid confidence values"
VALIDATION categories ("malformed JSON" is
`RadiologyInterpretationParserPort`'s concern, and "empty reports"/
"malformed reports" are `domain/value_objects.py`'s own `__post_init__`
concern on the caller-supplied *input* — a result that reaches this
validator already parsed successfully, so only content-level checks on
the AI's own *output* remain here, the same split every prior AI
module's own validator documents for itself).

Constructor-injected with `FollowUpRecommendationService` — this task's
own "Do NOT duplicate implementations" rule means duplicate-recommendation
*detection* lives once, on that application-layer service, and this
infrastructure-layer validator calls it rather than re-implementing the
same check (infrastructure depending on application is the same
direction Clean Architecture's dependency rule always allows). Duplicate-
*finding* detection has no equally natural owner among this task's own
four named application services (none of `FindingExtractionService`/
`CriticalFindingDetectionService`/`FollowUpRecommendationService`/
`RadiologySummaryService` is "finding list hygiene"), so that one check
is implemented directly here instead of forcing an artificial service
dependency onto an unrelated service.

Reuses `app.shared.infrastructure.text_processing.placeholder_detection
.find_placeholder_marker` (rule: "Reuse... Shared validator... Avoid
duplicate implementations").

Checks run in this order, each a distinct failure mode with its own
domain exception:

1. Any finding description reported more than once ->
   `DuplicateRadiologyFindingError`.
2. `confidence_score` present but outside `[0.0, 1.0]` ->
   `InvalidRadiologyConfidenceValueError`. `None` is not an error here:
   this module's confidence is always deterministically filled in by
   `MedicalReasoningAIPort.score_confidence` during enrichment (see
   `application/use_cases/interpret_radiology_report.py`), so a missing
   AI-reported value is expected, not invalid.
3. Any hallucinated placeholder in `examination_summary`,
   `clinical_significance`, `clinical_reasoning`, or any finding/
   recommendation/red-flag text -> `HallucinatedRadiologyFindingError`.
4. Any recommendation list (`differential_imaging_considerations`,
   `suggested_follow_up_imaging`, `suggested_specialist_referral`)
   containing the same entry twice (via
   `FollowUpRecommendationService.find_duplicate`) ->
   `InconsistentRadiologyRecommendationsError`.
"""

from app.modules.radiology_interpretation_ai.application.ports import (
    RadiologyInterpretationValidatorPort,
)
from app.modules.radiology_interpretation_ai.application.services.follow_up_recommendation_service import (  # noqa: E501
    FollowUpRecommendationService,
)
from app.modules.radiology_interpretation_ai.domain.exceptions import (
    DuplicateRadiologyFindingError,
    HallucinatedRadiologyFindingError,
    InconsistentRadiologyRecommendationsError,
    InvalidRadiologyConfidenceValueError,
)
from app.modules.radiology_interpretation_ai.domain.value_objects import (
    RadiologyInterpretationResult,
)
from app.shared.infrastructure.text_processing.placeholder_detection import (
    find_placeholder_marker,
)

_RECOMMENDATION_LISTS = (
    "differential_imaging_considerations",
    "suggested_follow_up_imaging",
    "suggested_specialist_referral",
)


class DefaultRadiologyInterpretationValidator(RadiologyInterpretationValidatorPort):
    def __init__(self, *, recommendation_service: FollowUpRecommendationService) -> None:
        self._recommendation_service = recommendation_service

    def validate(self, result: RadiologyInterpretationResult) -> None:
        self._check_duplicate_findings(result)
        self._check_confidence_value(result)
        self._check_hallucinated_placeholders(result)
        self._check_inconsistent_recommendations(result)

    def _check_duplicate_findings(self, result: RadiologyInterpretationResult) -> None:
        seen: set[str] = set()
        for finding in result.findings:
            normalized = finding.description.strip().lower()
            if not normalized:
                continue
            if normalized in seen:
                raise DuplicateRadiologyFindingError(finding.description)
            seen.add(normalized)

    def _check_confidence_value(self, result: RadiologyInterpretationResult) -> None:
        if result.confidence_score is not None and not (0.0 <= result.confidence_score <= 1.0):
            raise InvalidRadiologyConfidenceValueError()

    def _check_hallucinated_placeholders(self, result: RadiologyInterpretationResult) -> None:
        text_fields = (
            ("examination_summary", result.examination_summary),
            ("clinical_significance", result.clinical_significance),
            ("clinical_reasoning", result.clinical_reasoning),
        )
        for field_name, text in text_fields:
            placeholder = find_placeholder_marker(text)
            if placeholder is not None:
                raise HallucinatedRadiologyFindingError(field_name, placeholder)

        for finding in result.findings:
            placeholder = find_placeholder_marker(finding.description)
            if placeholder is not None:
                raise HallucinatedRadiologyFindingError("findings", placeholder)

        list_fields = (
            ("differential_imaging_considerations", result.differential_imaging_considerations),
            ("suggested_follow_up_imaging", result.suggested_follow_up_imaging),
            ("suggested_specialist_referral", result.suggested_specialist_referral),
            ("red_flag_warnings", result.red_flag_warnings),
        )
        for field_name, items in list_fields:
            for text in items:
                placeholder = find_placeholder_marker(text)
                if placeholder is not None:
                    raise HallucinatedRadiologyFindingError(field_name, placeholder)

    def _check_inconsistent_recommendations(self, result: RadiologyInterpretationResult) -> None:
        for list_name in _RECOMMENDATION_LISTS:
            items: tuple[str, ...] = getattr(result, list_name)
            duplicate = self._recommendation_service.find_duplicate(items)
            if duplicate is not None:
                raise InconsistentRadiologyRecommendationsError(list_name, duplicate)
