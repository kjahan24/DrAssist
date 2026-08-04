"""Domain exceptions for the AI Prescription Assistance module.

Errors originating from AI Foundation (`app.modules.ai`) — timeouts, rate
limits, authentication failures, provider unavailability, unregistered
prompt templates — are **not** wrapped or re-typed here and propagate
unchanged out of `infrastructure/generation/prescription_generator.py`,
the same "cannot import a peer module's `.domain`, so cannot
`isinstance`-check or re-wrap its exceptions" reasoning
`app.modules.icd10_ai.domain.exceptions`'s own module docstring
documents for the identical situation.
"""

from app.shared.domain.exceptions import DomainError


class InvalidPrescriptionContextError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"invalid prescription context: {reason}")
        self.reason = reason


class InvalidPrescriptionResponseFormatError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"could not parse AI output into prescription suggestions: {reason}")
        self.reason = reason


class EmptyPrescriptionResponseError(DomainError):
    def __init__(self) -> None:
        super().__init__("AI provider returned no medication suggestions")


class InvalidMedicationStructureError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"malformed medication suggestion: {reason}")
        self.reason = reason


class DuplicateMedicationError(DomainError):
    def __init__(self, generic_name: str) -> None:
        super().__init__(f"medication {generic_name!r} was suggested more than once")
        self.generic_name = generic_name


class MissingMedicationDosageError(DomainError):
    def __init__(self, generic_name: str) -> None:
        super().__init__(f"medication {generic_name!r} is missing a dosage")
        self.generic_name = generic_name


class MissingMedicationFrequencyError(DomainError):
    def __init__(self, generic_name: str) -> None:
        super().__init__(f"medication {generic_name!r} is missing a frequency")
        self.generic_name = generic_name


class MissingMedicationDurationError(DomainError):
    def __init__(self, generic_name: str) -> None:
        super().__init__(f"medication {generic_name!r} is missing a duration")
        self.generic_name = generic_name


class HallucinatedMedicationError(DomainError):
    def __init__(self, generic_name: str, placeholder: str) -> None:
        super().__init__(
            f"suggestion for {generic_name!r} contains an unresolved placeholder: {placeholder!r}"
        )
        self.generic_name = generic_name
        self.placeholder = placeholder
