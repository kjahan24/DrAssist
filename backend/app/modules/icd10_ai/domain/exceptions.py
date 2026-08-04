"""Domain exceptions for the AI ICD-10 Coding module.

Errors originating from AI Foundation (`app.modules.ai`) — timeouts, rate
limits, authentication failures, provider unavailability, unregistered
prompt templates — are **not** wrapped or re-typed here and propagate
unchanged out of `infrastructure/generation/icd10_generator.py`, the same
"cannot import a peer module's `.domain`, so cannot `isinstance`-check or
re-wrap its exceptions" reasoning
`app.modules.soap_note_ai.domain.exceptions`'s own module docstring
documents for the identical situation.
"""

from app.shared.domain.exceptions import DomainError


class InvalidClinicalContextError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"invalid ICD-10 clinical context: {reason}")
        self.reason = reason


class InvalidICD10ResponseFormatError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"could not parse AI output into ICD-10 suggestions: {reason}")
        self.reason = reason


class EmptyICD10ResponseError(DomainError):
    def __init__(self) -> None:
        super().__init__("AI provider returned no ICD-10 suggestions")


class InvalidICD10CodeError(DomainError):
    def __init__(self, icd10_code: str) -> None:
        super().__init__(f"{icd10_code!r} is not a structurally valid ICD-10-CM code")
        self.icd10_code = icd10_code


class DuplicateICD10CodeError(DomainError):
    def __init__(self, icd10_code: str) -> None:
        super().__init__(f"ICD-10 code {icd10_code!r} was suggested more than once")
        self.icd10_code = icd10_code


class HallucinatedDiagnosisError(DomainError):
    def __init__(self, icd10_code: str, placeholder: str) -> None:
        super().__init__(
            f"suggestion for {icd10_code!r} contains an unresolved placeholder: {placeholder!r}"
        )
        self.icd10_code = icd10_code
        self.placeholder = placeholder


class MissingConfidenceScoreError(DomainError):
    def __init__(self, icd10_code: str) -> None:
        super().__init__(
            f"suggestion for {icd10_code!r} is missing a valid confidence score in [0.0, 1.0]"
        )
        self.icd10_code = icd10_code
