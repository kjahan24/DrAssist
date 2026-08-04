"""Domain exceptions for the AI Clinical Note Generation module.

Errors originating from AI Foundation (`app.modules.ai`) — timeouts, rate
limits, authentication failures, provider unavailability, unregistered
prompt templates — are **not** wrapped or re-typed here and propagate
unchanged out of `infrastructure/generation/clinical_note_generator.py`,
the same "cannot import a peer module's `.domain`, so cannot
`isinstance`-check or re-wrap its exceptions" reasoning
`app.modules.ai_copilot.domain.exceptions`'s own module docstring
documents for the identical situation.
"""

from app.shared.domain.exceptions import DomainError


class InvalidClinicalEncounterInputError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"invalid clinical encounter input: {reason}")
        self.reason = reason


class MissingClinicalNoteSectionError(DomainError):
    def __init__(self, section_name: str) -> None:
        super().__init__(f"generated note is missing required section {section_name!r}")
        self.section_name = section_name


class EmptyAIResponseError(DomainError):
    def __init__(self) -> None:
        super().__init__("AI provider returned an empty response")


class HallucinatedPlaceholderError(DomainError):
    def __init__(self, section_name: str, placeholder: str) -> None:
        super().__init__(
            f"section {section_name!r} contains an unresolved placeholder: {placeholder!r}"
        )
        self.section_name = section_name
        self.placeholder = placeholder


class InvalidClinicalNoteFormatError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"could not parse AI output into a clinical note: {reason}")
        self.reason = reason
