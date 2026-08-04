"""Domain exceptions for the AI Lab Interpretation module.

Mapped one-to-one onto this task's own seven-item VALIDATION list:
"malformed lab data" -> `MalformedLabValueError`, "duplicate values" ->
`DuplicateLabValueError`, "impossible numeric ranges" ->
`ImpossibleLabValueRangeError`, "invalid units" -> `InvalidLabUnitError`
(all four raised from `domain/value_objects.py`'s own `__post_init__`
Tier-3 validation — the caller-supplied `lab_values` themselves, before
any AI call happens); "malformed AI output" ->
`InvalidLabInterpretationResponseFormatError` (the parser); "missing
reasoning" -> `MissingLabReasoningError`; "hallucinated values" ->
`HallucinatedLabValueError` (both the validator, on the AI's own
response). `InvalidLabInterpretationInputError` covers the remaining,
not-separately-named baseline input checks (blank language, an
out-of-range `patient_age`, an empty `lab_values` collection) every
prior AI module's own top-level input value object also performs for
itself.

Errors originating from AI Foundation (`app.modules.ai`) — timeouts,
rate limits, authentication failures, provider unavailability,
unregistered prompt templates — are **not** wrapped or re-typed here and
propagate unchanged out of `infrastructure/generation
/lab_interpretation_generator.py`, the same "cannot import a peer
module's `.domain`, so cannot `isinstance`-check or re-wrap its
exceptions" reasoning
`app.modules.medical_reasoning_ai.domain.exceptions`'s own module
docstring documents for the identical situation.
"""

from app.shared.domain.exceptions import DomainError


class InvalidLabInterpretationInputError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"invalid lab interpretation input: {reason}")
        self.reason = reason


class MalformedLabValueError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"malformed lab value: {reason}")
        self.reason = reason


class DuplicateLabValueError(DomainError):
    def __init__(self, test_name: str) -> None:
        super().__init__(f"lab value {test_name!r} was reported more than once")
        self.test_name = test_name


class ImpossibleLabValueRangeError(DomainError):
    def __init__(self, test_name: str) -> None:
        super().__init__(f"lab value {test_name!r} has an impossible numeric range")
        self.test_name = test_name


class InvalidLabUnitError(DomainError):
    def __init__(self, test_name: str) -> None:
        super().__init__(f"lab value {test_name!r} has an invalid unit")
        self.test_name = test_name


class InvalidLabInterpretationResponseFormatError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"could not parse AI output into a lab interpretation: {reason}")
        self.reason = reason


class MissingLabReasoningError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"generated lab interpretation is missing required content: {reason}")
        self.reason = reason


class HallucinatedLabValueError(DomainError):
    def __init__(self, field_name: str, placeholder: str) -> None:
        super().__init__(f"{field_name!r} contains an unresolved placeholder: {placeholder!r}")
        self.field_name = field_name
        self.placeholder = placeholder
