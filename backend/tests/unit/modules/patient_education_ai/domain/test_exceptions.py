"""Tests for the AI Patient Education & Discharge Instructions module's
domain exceptions — message content and attribute preservation."""

from app.modules.patient_education_ai.domain.exceptions import (
    HallucinatedRecommendationError,
    InvalidPatientEducationConfidenceValueError,
    InvalidPatientEducationInputError,
    InvalidPatientEducationResponseFormatError,
    MissingDiagnosisError,
    MissingMedicationListError,
    UnsafeInstructionError,
)
from app.shared.domain.exceptions import DomainError


class TestInvalidPatientEducationInputError:
    def test_is_domain_error(self) -> None:
        assert isinstance(InvalidPatientEducationInputError("bad"), DomainError)

    def test_message_includes_reason(self) -> None:
        error = InvalidPatientEducationInputError("patient_age must be non-negative")
        assert "patient_age must be non-negative" in str(error)

    def test_stores_reason_attribute(self) -> None:
        error = InvalidPatientEducationInputError("bad")
        assert error.reason == "bad"


class TestMissingDiagnosisError:
    def test_is_domain_error(self) -> None:
        assert isinstance(MissingDiagnosisError(), DomainError)

    def test_message(self) -> None:
        assert "at least one diagnosis" in str(MissingDiagnosisError())


class TestMissingMedicationListError:
    def test_is_domain_error(self) -> None:
        assert isinstance(MissingMedicationListError(), DomainError)

    def test_message(self) -> None:
        assert "at least one current medication" in str(MissingMedicationListError())


class TestInvalidPatientEducationResponseFormatError:
    def test_is_domain_error(self) -> None:
        assert isinstance(InvalidPatientEducationResponseFormatError("bad"), DomainError)

    def test_message_includes_reason(self) -> None:
        error = InvalidPatientEducationResponseFormatError("no JSON object found")
        assert "no JSON object found" in str(error)


class TestHallucinatedRecommendationError:
    def test_is_domain_error(self) -> None:
        error = HallucinatedRecommendationError("patient_summary", "[insert]")
        assert isinstance(error, DomainError)

    def test_message_includes_field_and_placeholder(self) -> None:
        error = HallucinatedRecommendationError("patient_summary", "[insert]")
        assert "patient_summary" in str(error)
        assert "[insert]" in str(error)

    def test_stores_attributes(self) -> None:
        error = HallucinatedRecommendationError("patient_summary", "[insert]")
        assert error.field_name == "patient_summary"
        assert error.placeholder == "[insert]"


class TestUnsafeInstructionError:
    def test_is_domain_error(self) -> None:
        error = UnsafeInstructionError("medication_instructions", "double your dose")
        assert isinstance(error, DomainError)

    def test_message_includes_field_and_phrase(self) -> None:
        error = UnsafeInstructionError("medication_instructions", "double your dose")
        assert "medication_instructions" in str(error)
        assert "double your dose" in str(error)

    def test_stores_attributes(self) -> None:
        error = UnsafeInstructionError("medication_instructions", "double your dose")
        assert error.field_name == "medication_instructions"
        assert error.phrase == "double your dose"


class TestInvalidPatientEducationConfidenceValueError:
    def test_is_domain_error(self) -> None:
        assert isinstance(InvalidPatientEducationConfidenceValueError(), DomainError)

    def test_message(self) -> None:
        assert "confidence_score" in str(InvalidPatientEducationConfidenceValueError())
