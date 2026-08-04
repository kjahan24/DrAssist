"""Unit tests for the AI Clinical Copilot module's domain exceptions."""

from uuid import uuid4

from app.modules.ai_copilot.domain.exceptions import (
    AIResponseValidationError,
    InvalidAIRequestError,
    PatientNotFoundError,
    StructuredResponseParsingError,
)
from app.shared.domain.exceptions import DomainError


class TestPatientNotFoundError:
    def test_message_includes_patient_id(self) -> None:
        patient_id = uuid4()
        exc = PatientNotFoundError(patient_id)
        assert str(patient_id) in str(exc)
        assert exc.patient_id == patient_id

    def test_is_a_domain_error(self) -> None:
        assert isinstance(PatientNotFoundError(uuid4()), DomainError)


class TestInvalidAIRequestError:
    def test_message_includes_reason(self) -> None:
        exc = InvalidAIRequestError("request_type must not be blank")
        assert "request_type must not be blank" in str(exc)
        assert exc.reason == "request_type must not be blank"


class TestStructuredResponseParsingError:
    def test_message_includes_format_and_reason(self) -> None:
        exc = StructuredResponseParsingError("json", "unexpected token")
        assert "json" in str(exc)
        assert "unexpected token" in str(exc)
        assert exc.output_format == "json"
        assert exc.reason == "unexpected token"


class TestAIResponseValidationError:
    def test_message_includes_reason(self) -> None:
        exc = AIResponseValidationError("JSON response was empty")
        assert "JSON response was empty" in str(exc)
        assert exc.reason == "JSON response was empty"


class TestAllDomainExceptionsAreDomainErrors:
    def test_invalid_ai_request_error(self) -> None:
        assert isinstance(InvalidAIRequestError("x"), DomainError)

    def test_structured_response_parsing_error(self) -> None:
        assert isinstance(StructuredResponseParsingError("json", "x"), DomainError)

    def test_ai_response_validation_error(self) -> None:
        assert isinstance(AIResponseValidationError("x"), DomainError)
