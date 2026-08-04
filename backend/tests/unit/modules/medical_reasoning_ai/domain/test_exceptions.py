"""Unit tests for the AI Medical Reasoning Engine's domain exceptions."""

from app.modules.medical_reasoning_ai.domain.exceptions import (
    DuplicateEvidenceError,
    EmptyReasoningResponseError,
    HallucinatedReasoningPlaceholderError,
    InconsistentRecommendationsError,
    InvalidConfidenceValueError,
    InvalidMedicalReasoningInputError,
    InvalidMedicalReasoningResponseFormatError,
    MissingReasoningError,
)
from app.shared.domain.exceptions import DomainError


class TestInvalidMedicalReasoningInputError:
    def test_message_includes_reason(self) -> None:
        exc = InvalidMedicalReasoningInputError("chief_complaint must not be blank")
        assert "chief_complaint must not be blank" in str(exc)
        assert exc.reason == "chief_complaint must not be blank"


class TestInvalidMedicalReasoningResponseFormatError:
    def test_message_includes_reason(self) -> None:
        exc = InvalidMedicalReasoningResponseFormatError("malformed JSON")
        assert "malformed JSON" in str(exc)
        assert exc.reason == "malformed JSON"


class TestEmptyReasoningResponseError:
    def test_has_a_stable_message(self) -> None:
        assert "empty reasoning response" in str(EmptyReasoningResponseError())


class TestMissingReasoningError:
    def test_message_includes_reason(self) -> None:
        exc = MissingReasoningError("clinical_summary must not be blank")
        assert "clinical_summary must not be blank" in str(exc)
        assert exc.reason == "clinical_summary must not be blank"


class TestDuplicateEvidenceError:
    def test_message_includes_the_description(self) -> None:
        exc = DuplicateEvidenceError("Fever present")
        assert "Fever present" in str(exc)
        assert exc.description == "Fever present"


class TestInvalidConfidenceValueError:
    def test_message_includes_the_dimension(self) -> None:
        exc = InvalidConfidenceValueError("clinical")
        assert "clinical" in str(exc)
        assert exc.dimension == "clinical"


class TestHallucinatedReasoningPlaceholderError:
    def test_message_includes_field_and_placeholder(self) -> None:
        exc = HallucinatedReasoningPlaceholderError("clinical_summary", "[INSERT SUMMARY]")
        assert "clinical_summary" in str(exc)
        assert "[INSERT SUMMARY]" in str(exc)
        assert exc.field_name == "clinical_summary"
        assert exc.placeholder == "[INSERT SUMMARY]"


class TestInconsistentRecommendationsError:
    def test_message_includes_list_name_and_item(self) -> None:
        exc = InconsistentRecommendationsError("suggested_investigations", "CBC")
        assert "suggested_investigations" in str(exc)
        assert "CBC" in str(exc)
        assert exc.list_name == "suggested_investigations"
        assert exc.item == "CBC"


class TestAllDomainExceptionsAreDomainErrors:
    def test_invalid_medical_reasoning_input_error(self) -> None:
        assert isinstance(InvalidMedicalReasoningInputError("x"), DomainError)

    def test_invalid_medical_reasoning_response_format_error(self) -> None:
        assert isinstance(InvalidMedicalReasoningResponseFormatError("x"), DomainError)

    def test_empty_reasoning_response_error(self) -> None:
        assert isinstance(EmptyReasoningResponseError(), DomainError)

    def test_missing_reasoning_error(self) -> None:
        assert isinstance(MissingReasoningError("x"), DomainError)

    def test_duplicate_evidence_error(self) -> None:
        assert isinstance(DuplicateEvidenceError("x"), DomainError)

    def test_invalid_confidence_value_error(self) -> None:
        assert isinstance(InvalidConfidenceValueError("x"), DomainError)

    def test_hallucinated_reasoning_placeholder_error(self) -> None:
        assert isinstance(HallucinatedReasoningPlaceholderError("x", "y"), DomainError)

    def test_inconsistent_recommendations_error(self) -> None:
        assert isinstance(InconsistentRecommendationsError("x", "y"), DomainError)
