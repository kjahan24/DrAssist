"""Domain exceptions for the AI Medical Reasoning Engine.

Errors originating from AI Foundation (`app.modules.ai`) — timeouts, rate
limits, authentication failures, provider unavailability, unregistered
prompt templates — are **not** wrapped or re-typed here and propagate
unchanged out of `infrastructure/generation/medical_reasoning_generator.py`,
the same "cannot import a peer module's `.domain`, so cannot
`isinstance`-check or re-wrap its exceptions" reasoning
`app.modules.differential_diagnosis_ai.domain.exceptions`'s own module
docstring documents for the identical situation.
"""

from app.shared.domain.exceptions import DomainError


class InvalidMedicalReasoningInputError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"invalid medical reasoning input: {reason}")
        self.reason = reason


class InvalidMedicalReasoningResponseFormatError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"could not parse AI output into medical reasoning: {reason}")
        self.reason = reason


class EmptyReasoningResponseError(DomainError):
    def __init__(self) -> None:
        super().__init__("AI provider returned an empty reasoning response")


class MissingReasoningError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"generated reasoning is missing required content: {reason}")
        self.reason = reason


class DuplicateEvidenceError(DomainError):
    def __init__(self, description: str) -> None:
        super().__init__(f"evidence item {description!r} was reported more than once")
        self.description = description


class InvalidConfidenceValueError(DomainError):
    def __init__(self, dimension: str) -> None:
        super().__init__(f"{dimension} confidence must be within [0.0, 1.0] when given")
        self.dimension = dimension


class HallucinatedReasoningPlaceholderError(DomainError):
    def __init__(self, field_name: str, placeholder: str) -> None:
        super().__init__(f"{field_name!r} contains an unresolved placeholder: {placeholder!r}")
        self.field_name = field_name
        self.placeholder = placeholder


class InconsistentRecommendationsError(DomainError):
    def __init__(self, list_name: str, item: str) -> None:
        super().__init__(f"{list_name!r} contains a duplicated recommendation: {item!r}")
        self.list_name = list_name
        self.item = item
