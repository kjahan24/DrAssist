"""Unit tests for the AI Clinical Note Generation module's domain
exceptions."""

from app.modules.clinical_note_ai.domain.exceptions import (
    EmptyAIResponseError,
    HallucinatedPlaceholderError,
    InvalidClinicalEncounterInputError,
    InvalidClinicalNoteFormatError,
    MissingClinicalNoteSectionError,
)
from app.shared.domain.exceptions import DomainError


class TestInvalidClinicalEncounterInputError:
    def test_message_includes_reason(self) -> None:
        exc = InvalidClinicalEncounterInputError("chief_complaint must not be blank")
        assert "chief_complaint must not be blank" in str(exc)
        assert exc.reason == "chief_complaint must not be blank"


class TestMissingClinicalNoteSectionError:
    def test_message_includes_section_name(self) -> None:
        exc = MissingClinicalNoteSectionError("assessment")
        assert "assessment" in str(exc)
        assert exc.section_name == "assessment"


class TestEmptyAIResponseError:
    def test_has_a_stable_message(self) -> None:
        assert "empty" in str(EmptyAIResponseError()).lower()


class TestHallucinatedPlaceholderError:
    def test_message_includes_section_and_placeholder(self) -> None:
        exc = HallucinatedPlaceholderError("plan", "[INSERT PLAN]")
        assert "plan" in str(exc)
        assert "[INSERT PLAN]" in str(exc)
        assert exc.section_name == "plan"
        assert exc.placeholder == "[INSERT PLAN]"


class TestInvalidClinicalNoteFormatError:
    def test_message_includes_reason(self) -> None:
        exc = InvalidClinicalNoteFormatError("malformed JSON")
        assert "malformed JSON" in str(exc)
        assert exc.reason == "malformed JSON"


class TestAllDomainExceptionsAreDomainErrors:
    def test_invalid_clinical_encounter_input_error(self) -> None:
        assert isinstance(InvalidClinicalEncounterInputError("x"), DomainError)

    def test_missing_clinical_note_section_error(self) -> None:
        assert isinstance(MissingClinicalNoteSectionError("x"), DomainError)

    def test_empty_ai_response_error(self) -> None:
        assert isinstance(EmptyAIResponseError(), DomainError)

    def test_hallucinated_placeholder_error(self) -> None:
        assert isinstance(HallucinatedPlaceholderError("x", "y"), DomainError)

    def test_invalid_clinical_note_format_error(self) -> None:
        assert isinstance(InvalidClinicalNoteFormatError("x"), DomainError)
