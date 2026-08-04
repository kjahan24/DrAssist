"""Domain exceptions for the AI SOAP Note Generation module.

Errors originating from AI Foundation (`app.modules.ai`) — timeouts, rate
limits, authentication failures, provider unavailability, unregistered
prompt templates — are **not** wrapped or re-typed here and propagate
unchanged out of `infrastructure/generation/soap_note_generator.py`, the
same "cannot import a peer module's `.domain`, so cannot `isinstance`-
check or re-wrap its exceptions" reasoning
`app.modules.clinical_note_ai.domain.exceptions`'s own module docstring
documents for the identical situation.
"""

from app.shared.domain.exceptions import DomainError


class InvalidSOAPEncounterInputError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"invalid SOAP encounter input: {reason}")
        self.reason = reason


class MissingSOAPSectionError(DomainError):
    def __init__(self, section_name: str) -> None:
        super().__init__(f"generated SOAP note is missing required section {section_name!r}")
        self.section_name = section_name


class EmptySOAPResponseError(DomainError):
    def __init__(self) -> None:
        super().__init__("AI provider returned an empty response")


class DuplicatedSOAPSectionError(DomainError):
    def __init__(self, first_section: str, second_section: str) -> None:
        super().__init__(
            f"sections {first_section!r} and {second_section!r} contain identical content — "
            "the model likely failed to differentiate them"
        )
        self.first_section = first_section
        self.second_section = second_section


class HallucinatedPlaceholderError(DomainError):
    def __init__(self, section_name: str, placeholder: str) -> None:
        super().__init__(
            f"section {section_name!r} contains an unresolved placeholder: {placeholder!r}"
        )
        self.section_name = section_name
        self.placeholder = placeholder


class InvalidMarkdownFormatError(DomainError):
    def __init__(self, section_name: str, reason: str) -> None:
        super().__init__(f"section {section_name!r} contains malformed markdown: {reason}")
        self.section_name = section_name
        self.reason = reason


class InvalidSOAPNoteFormatError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"could not parse AI output into a SOAP note: {reason}")
        self.reason = reason
