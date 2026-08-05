"""Domain exceptions for the AI Patient Education & Discharge
Instructions module.

Mapped one-to-one onto this task's own six-item VALIDATION list:
"missing diagnosis" -> `MissingDiagnosisError`, "missing medication
list" -> `MissingMedicationListError` (both raised from `domain
/value_objects.py`'s own `__post_init__` Tier-3 validation — the
caller-supplied clinical data itself, before any AI call happens);
"malformed JSON" -> `InvalidPatientEducationResponseFormatError` (the
parser); "hallucinated recommendations" -> `HallucinatedRecommendationError`,
"unsafe instructions" -> `UnsafeInstructionError`, "invalid confidence"
-> `InvalidPatientEducationConfidenceValueError` (all three raised by
the validator, on the AI's own response). `InvalidPatientEducationInputError`
covers the remaining, not-separately-named baseline input checks (a
blank `language`, an out-of-range `patient_age`) every prior AI
module's own top-level input value object also performs for itself.

`UnsafeInstructionError` is this module's own addition, beyond the
shape every prior AI module's own domain exceptions establish — this
task's own GOAL section is explicit that this module "MUST NOT replace
physician counselling", so a curated, deterministic safety net
(`infrastructure/validation/patient_education_validator.py`) scans every
generated instruction for known-dangerous phrasing (e.g. "double your
dose", "stop taking all medications", "no need to see a doctor") and
raises this exception rather than letting unsafe guidance reach a
patient — the sharpest-edged instance of the "deterministic floor/
override" safety-net pattern every prior AI module's own enrichment
step applies for itself, applied here as an outright rejection instead
of a silent correction, because there is no safe deterministic
correction for a hallucinated unsafe instruction.

Errors originating from AI Foundation (`app.modules.ai`) — timeouts,
rate limits, authentication failures, provider unavailability,
unregistered prompt templates — are **not** wrapped or re-typed here and
propagate unchanged out of `infrastructure/generation
/patient_education_generator.py`, the same "cannot import a peer
module's `.domain`, so cannot `isinstance`-check or re-wrap its
exceptions" reasoning every prior AI module's own domain exceptions
module docstring documents for the identical situation.
"""

from app.shared.domain.exceptions import DomainError


class InvalidPatientEducationInputError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"invalid patient education input: {reason}")
        self.reason = reason


class MissingDiagnosisError(DomainError):
    def __init__(self) -> None:
        super().__init__("at least one diagnosis must be provided")


class MissingMedicationListError(DomainError):
    def __init__(self) -> None:
        super().__init__("at least one current medication must be provided")


class InvalidPatientEducationResponseFormatError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"could not parse AI output into a patient education result: {reason}")
        self.reason = reason


class HallucinatedRecommendationError(DomainError):
    def __init__(self, field_name: str, placeholder: str) -> None:
        super().__init__(f"{field_name!r} contains an unresolved placeholder: {placeholder!r}")
        self.field_name = field_name
        self.placeholder = placeholder


class UnsafeInstructionError(DomainError):
    def __init__(self, field_name: str, phrase: str) -> None:
        super().__init__(f"{field_name!r} contains an unsafe instruction phrase: {phrase!r}")
        self.field_name = field_name
        self.phrase = phrase


class InvalidPatientEducationConfidenceValueError(DomainError):
    def __init__(self) -> None:
        super().__init__("confidence_score must be within [0.0, 1.0] when given")
