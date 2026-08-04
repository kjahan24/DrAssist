"""Unit tests for the AI SOAP Note Generation module's domain
exceptions."""

from app.modules.soap_note_ai.domain.exceptions import (
    DuplicatedSOAPSectionError,
    EmptySOAPResponseError,
    HallucinatedPlaceholderError,
    InvalidMarkdownFormatError,
    InvalidSOAPEncounterInputError,
    InvalidSOAPNoteFormatError,
    MissingSOAPSectionError,
)
from app.shared.domain.exceptions import DomainError


class TestInvalidSOAPEncounterInputError:
    def test_message_includes_reason(self) -> None:
        exc = InvalidSOAPEncounterInputError("chief_complaint must not be blank")
        assert "chief_complaint must not be blank" in str(exc)
        assert exc.reason == "chief_complaint must not be blank"


class TestMissingSOAPSectionError:
    def test_message_includes_section_name(self) -> None:
        exc = MissingSOAPSectionError("plan")
        assert "plan" in str(exc)
        assert exc.section_name == "plan"


class TestEmptySOAPResponseError:
    def test_has_a_stable_message(self) -> None:
        assert "empty" in str(EmptySOAPResponseError()).lower()


class TestDuplicatedSOAPSectionError:
    def test_message_includes_both_section_names(self) -> None:
        exc = DuplicatedSOAPSectionError("subjective", "objective")
        assert "subjective" in str(exc)
        assert "objective" in str(exc)
        assert exc.first_section == "subjective"
        assert exc.second_section == "objective"


class TestHallucinatedPlaceholderError:
    def test_message_includes_section_and_placeholder(self) -> None:
        exc = HallucinatedPlaceholderError("plan", "[INSERT PLAN]")
        assert "plan" in str(exc)
        assert "[INSERT PLAN]" in str(exc)


class TestInvalidMarkdownFormatError:
    def test_message_includes_section_and_reason(self) -> None:
        exc = InvalidMarkdownFormatError("assessment", "unbalanced code fence")
        assert "assessment" in str(exc)
        assert "unbalanced code fence" in str(exc)
        assert exc.section_name == "assessment"
        assert exc.reason == "unbalanced code fence"


class TestInvalidSOAPNoteFormatError:
    def test_message_includes_reason(self) -> None:
        exc = InvalidSOAPNoteFormatError("malformed JSON")
        assert "malformed JSON" in str(exc)


class TestAllDomainExceptionsAreDomainErrors:
    def test_invalid_soap_encounter_input_error(self) -> None:
        assert isinstance(InvalidSOAPEncounterInputError("x"), DomainError)

    def test_missing_soap_section_error(self) -> None:
        assert isinstance(MissingSOAPSectionError("x"), DomainError)

    def test_empty_soap_response_error(self) -> None:
        assert isinstance(EmptySOAPResponseError(), DomainError)

    def test_duplicated_soap_section_error(self) -> None:
        assert isinstance(DuplicatedSOAPSectionError("x", "y"), DomainError)

    def test_hallucinated_placeholder_error(self) -> None:
        assert isinstance(HallucinatedPlaceholderError("x", "y"), DomainError)

    def test_invalid_markdown_format_error(self) -> None:
        assert isinstance(InvalidMarkdownFormatError("x", "y"), DomainError)

    def test_invalid_soap_note_format_error(self) -> None:
        assert isinstance(InvalidSOAPNoteFormatError("x"), DomainError)
