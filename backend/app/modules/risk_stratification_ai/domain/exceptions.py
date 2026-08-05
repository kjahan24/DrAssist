"""Domain exceptions for the AI Risk Stratification & Early Warning
Score module.

Mapped one-to-one onto this task's own six-item VALIDATION list:
"missing vital signs" -> `MissingVitalSignsError`, "incomplete
laboratory values" -> `IncompleteLaboratoryValueError` (both raised from
`domain/value_objects.py`'s own `__post_init__` Tier-3 validation — the
caller-supplied clinical data itself, before any AI call happens);
"malformed JSON" -> `InvalidRiskStratificationResponseFormatError` (the
parser); "invalid scores" -> `InvalidRiskScoreError`, "hallucinated risk
factors" -> `HallucinatedRiskFactorError`, "invalid confidence" ->
`InvalidRiskConfidenceValueError` (all three raised by the validator, on
the AI's own response). `InvalidRiskStratificationInputError` covers the
remaining, not-separately-named baseline input checks (a blank
`language`, an out-of-range `patient_age`, an implausible raw vital-sign
reading) every prior AI module's own top-level input value object also
performs for itself.

Errors originating from AI Foundation (`app.modules.ai`) — timeouts,
rate limits, authentication failures, provider unavailability,
unregistered prompt templates — are **not** wrapped or re-typed here and
propagate unchanged out of `infrastructure/generation
/risk_stratification_generator.py`, the same "cannot import a peer
module's `.domain`, so cannot `isinstance`-check or re-wrap its
exceptions" reasoning every prior AI module's own domain exceptions
module docstring documents for the identical situation.
"""

from app.shared.domain.exceptions import DomainError


class InvalidRiskStratificationInputError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"invalid risk stratification input: {reason}")
        self.reason = reason


class MissingVitalSignsError(DomainError):
    def __init__(self) -> None:
        super().__init__("at least one vital sign reading must be provided")


class IncompleteLaboratoryValueError(DomainError):
    def __init__(self, test_name: str) -> None:
        super().__init__(
            f"laboratory value {test_name!r} is missing both a reported value and a "
            "numeric value"
        )
        self.test_name = test_name


class InvalidRiskStratificationResponseFormatError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"could not parse AI output into a risk stratification: {reason}")
        self.reason = reason


class InvalidRiskScoreError(DomainError):
    def __init__(self, category: str, score_value: float) -> None:
        super().__init__(f"{category!r} score {score_value!r} is outside its valid range")
        self.category = category
        self.score_value = score_value


class HallucinatedRiskFactorError(DomainError):
    def __init__(self, field_name: str, placeholder: str) -> None:
        super().__init__(f"{field_name!r} contains an unresolved placeholder: {placeholder!r}")
        self.field_name = field_name
        self.placeholder = placeholder


class InvalidRiskConfidenceValueError(DomainError):
    def __init__(self) -> None:
        super().__init__("confidence_score must be within [0.0, 1.0] when given")
