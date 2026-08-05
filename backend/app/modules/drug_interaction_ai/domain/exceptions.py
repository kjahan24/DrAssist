"""Domain exceptions for the AI Drug Interaction & Medication Safety
module.

Mapped one-to-one onto this task's own seven-item VALIDATION list:
"empty medication lists" -> `EmptyMedicationListError`, "duplicate
medications" -> `DuplicateMedicationError` (both raised from `domain
/value_objects.py`'s own `__post_init__` Tier-3 validation — the
caller-supplied medication lists themselves, before any AI call
happens); "malformed JSON" -> `InvalidDrugInteractionResponseFormatError`
(the parser); "unknown medications" -> `UnknownMedicationError`,
"hallucinated interactions" -> `HallucinatedInteractionError`, "invalid
confidence" -> `InvalidDrugInteractionConfidenceValueError`, "missing
required evidence" -> `MissingInteractionEvidenceError` (all four raised
by the validator, on the AI's own response — see
`infrastructure/validation/drug_interaction_validator.py`'s own module
docstring for why "unknown medications" is an *output*-side check here,
not an input-side one: it means the AI's response references a
medication the caller never actually supplied, not a caller-supplied
name this module fails to recognize).
`InvalidDrugInteractionInputError` covers the remaining, not-separately-
named baseline input checks (a blank medication `drug_name`, a blank
`language`, an out-of-range `patient_age`/`patient_weight_kg`) every
prior AI module's own top-level input value object also performs for
itself.

Errors originating from AI Foundation (`app.modules.ai`) — timeouts,
rate limits, authentication failures, provider unavailability,
unregistered prompt templates — are **not** wrapped or re-typed here and
propagate unchanged out of `infrastructure/generation
/drug_safety_analysis_generator.py`, the same "cannot import a peer
module's `.domain`, so cannot `isinstance`-check or re-wrap its
exceptions" reasoning every prior AI module's own domain exceptions
module docstring documents for the identical situation.
"""

from app.shared.domain.exceptions import DomainError


class InvalidDrugInteractionInputError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"invalid drug interaction analysis input: {reason}")
        self.reason = reason


class EmptyMedicationListError(DomainError):
    def __init__(self) -> None:
        super().__init__("at least one of current_medications or new_prescription must be provided")


class DuplicateMedicationError(DomainError):
    def __init__(self, drug_name: str) -> None:
        super().__init__(f"medication {drug_name!r} was reported more than once")
        self.drug_name = drug_name


class InvalidDrugInteractionResponseFormatError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"could not parse AI output into a drug safety analysis: {reason}")
        self.reason = reason


class UnknownMedicationError(DomainError):
    def __init__(self, medication_name: str) -> None:
        super().__init__(f"{medication_name!r} was not among the medications supplied for analysis")
        self.medication_name = medication_name


class HallucinatedInteractionError(DomainError):
    def __init__(self, field_name: str, placeholder: str) -> None:
        super().__init__(f"{field_name!r} contains an unresolved placeholder: {placeholder!r}")
        self.field_name = field_name
        self.placeholder = placeholder


class InvalidDrugInteractionConfidenceValueError(DomainError):
    def __init__(self) -> None:
        super().__init__("confidence_score must be within [0.0, 1.0] when given")


class MissingInteractionEvidenceError(DomainError):
    def __init__(self, description: str) -> None:
        super().__init__(
            f"interaction {description!r} is severe enough to require an evidence level"
        )
        self.description = description
