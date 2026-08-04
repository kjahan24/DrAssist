"""Domain exceptions for the AI Differential Diagnosis module.

Errors originating from AI Foundation (`app.modules.ai`) — timeouts, rate
limits, authentication failures, provider unavailability, unregistered
prompt templates — are **not** wrapped or re-typed here and propagate
unchanged out of `infrastructure/generation/differential_diagnosis_generator.py`,
the same "cannot import a peer module's `.domain`, so cannot
`isinstance`-check or re-wrap its exceptions" reasoning
`app.modules.prescription_ai.domain.exceptions`'s own module docstring
documents for the identical situation.
"""

from app.shared.domain.exceptions import DomainError


class InvalidClinicalEvidenceError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"invalid clinical evidence: {reason}")
        self.reason = reason


class InvalidDifferentialResponseFormatError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"could not parse AI output into a differential diagnosis: {reason}")
        self.reason = reason


class EmptyDifferentialResponseError(DomainError):
    def __init__(self) -> None:
        super().__init__("AI provider returned no differential diagnosis candidates")


class DuplicateDiagnosisError(DomainError):
    def __init__(self, disease_name: str) -> None:
        super().__init__(f"diagnosis {disease_name!r} was suggested more than once")
        self.disease_name = disease_name


class HallucinatedDiagnosisError(DomainError):
    def __init__(self, disease_name: str, placeholder: str) -> None:
        super().__init__(
            f"candidate for {disease_name!r} contains an unresolved placeholder: {placeholder!r}"
        )
        self.disease_name = disease_name
        self.placeholder = placeholder


class InvalidConfidenceScoreError(DomainError):
    def __init__(self, disease_name: str) -> None:
        super().__init__(
            f"candidate for {disease_name!r} is missing a valid confidence score in [0.0, 1.0]"
        )
        self.disease_name = disease_name


class InvalidRankingError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"candidates are not validly ranked: {reason}")
        self.reason = reason


class InconsistentReasoningError(DomainError):
    def __init__(self, disease_name: str, reason: str) -> None:
        super().__init__(f"candidate for {disease_name!r} has inconsistent reasoning: {reason}")
        self.disease_name = disease_name
        self.reason = reason
