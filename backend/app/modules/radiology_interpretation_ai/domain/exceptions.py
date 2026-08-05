"""Domain exceptions for the AI Radiology Interpretation module.

Mapped one-to-one onto this task's own seven-item VALIDATION list:
"empty reports" -> `EmptyRadiologyReportError`, "malformed reports" ->
`MalformedRadiologyReportError` (both raised from `domain
/value_objects.py`'s own `__post_init__` Tier-3 validation — the
caller-supplied `report_text` itself, before any AI call happens);
"malformed JSON" -> `InvalidRadiologyInterpretationResponseFormatError`
(the parser); "duplicated findings" -> `DuplicateRadiologyFindingError`,
"hallucinated findings" -> `HallucinatedRadiologyFindingError",
"inconsistent recommendations" -> `InconsistentRadiologyRecommendationsError`,
"invalid confidence values" -> `InvalidRadiologyConfidenceValueError`
(all three raised by the validator, on the AI's own response).
`InvalidRadiologyInterpretationInputError` covers the remaining,
not-separately-named baseline input checks (blank language, an
out-of-range `patient_age`) every prior AI module's own top-level input
value object also performs for itself.

This task's VALIDATION list does not name a "missing reasoning"/"empty
outputs" category the way some prior AI modules' own tasks did — so,
deliberately, no such exception exists here (a blank AI-reported
`examination_summary`/`clinical_reasoning` becomes an empty string via
lenient parsing rather than a validation failure), matching this task's
own, more narrowly-scoped seven-category list exactly rather than
reintroducing a category from a different module's own task.

Errors originating from AI Foundation (`app.modules.ai`) — timeouts,
rate limits, authentication failures, provider unavailability,
unregistered prompt templates — are **not** wrapped or re-typed here and
propagate unchanged out of `infrastructure/generation
/radiology_interpretation_generator.py`, the same "cannot import a peer
module's `.domain`, so cannot `isinstance`-check or re-wrap its
exceptions" reasoning every prior AI module's own domain exceptions
module docstring documents for the identical situation.
"""

from app.shared.domain.exceptions import DomainError


class InvalidRadiologyInterpretationInputError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"invalid radiology interpretation input: {reason}")
        self.reason = reason


class EmptyRadiologyReportError(DomainError):
    def __init__(self) -> None:
        super().__init__("report_text must not be empty")


class MalformedRadiologyReportError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"malformed radiology report: {reason}")
        self.reason = reason


class InvalidRadiologyInterpretationResponseFormatError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"could not parse AI output into a radiology interpretation: {reason}")
        self.reason = reason


class DuplicateRadiologyFindingError(DomainError):
    def __init__(self, description: str) -> None:
        super().__init__(f"finding {description!r} was reported more than once")
        self.description = description


class HallucinatedRadiologyFindingError(DomainError):
    def __init__(self, field_name: str, placeholder: str) -> None:
        super().__init__(f"{field_name!r} contains an unresolved placeholder: {placeholder!r}")
        self.field_name = field_name
        self.placeholder = placeholder


class InconsistentRadiologyRecommendationsError(DomainError):
    def __init__(self, list_name: str, item: str) -> None:
        super().__init__(f"{list_name!r} contains a duplicated recommendation: {item!r}")
        self.list_name = list_name
        self.item = item


class InvalidRadiologyConfidenceValueError(DomainError):
    def __init__(self) -> None:
        super().__init__("confidence_score must be within [0.0, 1.0] when given")
