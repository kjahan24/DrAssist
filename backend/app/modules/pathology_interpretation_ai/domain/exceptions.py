"""Domain exceptions for the AI Pathology Interpretation module.

Mapped one-to-one onto this task's own seven-item VALIDATION list:
"empty reports" -> `EmptyPathologyReportError`, "malformed reports" ->
`MalformedPathologyReportError` (both raised from `domain
/value_objects.py`'s own `__post_init__` Tier-3 validation — the
caller-supplied `report_text` itself, before any AI call happens);
"malformed JSON" -> `InvalidPathologyInterpretationResponseFormatError`
(the parser); "duplicated findings" -> `DuplicatePathologyFindingError`,
"hallucinated findings" -> `HallucinatedPathologyFindingError`,
"inconsistent conclusions" -> `InconsistentPathologyConclusionsError`,
"invalid confidence values" -> `InvalidPathologyConfidenceValueError`
(all three raised by the validator, on the AI's own response).
`InvalidPathologyInterpretationInputError` covers the remaining,
not-separately-named baseline input checks (blank language, an
out-of-range `patient_age`) every prior AI module's own top-level input
value object also performs for itself.

Errors originating from AI Foundation (`app.modules.ai`) — timeouts,
rate limits, authentication failures, provider unavailability,
unregistered prompt templates — are **not** wrapped or re-typed here and
propagate unchanged out of `infrastructure/generation
/pathology_interpretation_generator.py`, the same "cannot import a peer
module's `.domain`, so cannot `isinstance`-check or re-wrap its
exceptions" reasoning every prior AI module's own domain exceptions
module docstring documents for the identical situation.
"""

from app.shared.domain.exceptions import DomainError


class InvalidPathologyInterpretationInputError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"invalid pathology interpretation input: {reason}")
        self.reason = reason


class EmptyPathologyReportError(DomainError):
    def __init__(self) -> None:
        super().__init__("report_text must not be empty")


class MalformedPathologyReportError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"malformed pathology report: {reason}")
        self.reason = reason


class InvalidPathologyInterpretationResponseFormatError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"could not parse AI output into a pathology interpretation: {reason}")
        self.reason = reason


class DuplicatePathologyFindingError(DomainError):
    def __init__(self, description: str) -> None:
        super().__init__(f"finding {description!r} was reported more than once")
        self.description = description


class HallucinatedPathologyFindingError(DomainError):
    def __init__(self, field_name: str, placeholder: str) -> None:
        super().__init__(f"{field_name!r} contains an unresolved placeholder: {placeholder!r}")
        self.field_name = field_name
        self.placeholder = placeholder


class InconsistentPathologyConclusionsError(DomainError):
    def __init__(self, list_name: str, item: str) -> None:
        super().__init__(f"{list_name!r} contains a duplicated conclusion: {item!r}")
        self.list_name = list_name
        self.item = item


class InvalidPathologyConfidenceValueError(DomainError):
    def __init__(self) -> None:
        super().__init__("confidence_score must be within [0.0, 1.0] when given")
