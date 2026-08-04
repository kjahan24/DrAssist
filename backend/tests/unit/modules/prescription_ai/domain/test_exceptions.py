"""Unit tests for the AI Prescription Assistance module's domain
exceptions."""

from app.modules.prescription_ai.domain.exceptions import (
    DuplicateMedicationError,
    EmptyPrescriptionResponseError,
    HallucinatedMedicationError,
    InvalidMedicationStructureError,
    InvalidPrescriptionContextError,
    InvalidPrescriptionResponseFormatError,
    MissingMedicationDosageError,
    MissingMedicationDurationError,
    MissingMedicationFrequencyError,
)
from app.shared.domain.exceptions import DomainError


class TestInvalidPrescriptionContextError:
    def test_message_includes_reason(self) -> None:
        exc = InvalidPrescriptionContextError("chief_complaint must not be blank")
        assert "chief_complaint must not be blank" in str(exc)
        assert exc.reason == "chief_complaint must not be blank"


class TestInvalidPrescriptionResponseFormatError:
    def test_message_includes_reason(self) -> None:
        exc = InvalidPrescriptionResponseFormatError("malformed JSON")
        assert "malformed JSON" in str(exc)
        assert exc.reason == "malformed JSON"


class TestEmptyPrescriptionResponseError:
    def test_has_a_stable_message(self) -> None:
        assert "no medication suggestions" in str(EmptyPrescriptionResponseError())


class TestInvalidMedicationStructureError:
    def test_message_includes_reason(self) -> None:
        exc = InvalidMedicationStructureError("generic_name must not be blank")
        assert "generic_name must not be blank" in str(exc)
        assert exc.reason == "generic_name must not be blank"


class TestDuplicateMedicationError:
    def test_message_includes_the_generic_name(self) -> None:
        exc = DuplicateMedicationError("ibuprofen")
        assert "ibuprofen" in str(exc)
        assert exc.generic_name == "ibuprofen"


class TestMissingMedicationDosageError:
    def test_message_includes_the_generic_name(self) -> None:
        exc = MissingMedicationDosageError("ibuprofen")
        assert "ibuprofen" in str(exc)
        assert exc.generic_name == "ibuprofen"


class TestMissingMedicationFrequencyError:
    def test_message_includes_the_generic_name(self) -> None:
        exc = MissingMedicationFrequencyError("ibuprofen")
        assert "ibuprofen" in str(exc)
        assert exc.generic_name == "ibuprofen"


class TestMissingMedicationDurationError:
    def test_message_includes_the_generic_name(self) -> None:
        exc = MissingMedicationDurationError("ibuprofen")
        assert "ibuprofen" in str(exc)
        assert exc.generic_name == "ibuprofen"


class TestHallucinatedMedicationError:
    def test_message_includes_name_and_placeholder(self) -> None:
        exc = HallucinatedMedicationError("ibuprofen", "[INSERT REASON]")
        assert "ibuprofen" in str(exc)
        assert "[INSERT REASON]" in str(exc)
        assert exc.generic_name == "ibuprofen"
        assert exc.placeholder == "[INSERT REASON]"


class TestAllDomainExceptionsAreDomainErrors:
    def test_invalid_prescription_context_error(self) -> None:
        assert isinstance(InvalidPrescriptionContextError("x"), DomainError)

    def test_invalid_prescription_response_format_error(self) -> None:
        assert isinstance(InvalidPrescriptionResponseFormatError("x"), DomainError)

    def test_empty_prescription_response_error(self) -> None:
        assert isinstance(EmptyPrescriptionResponseError(), DomainError)

    def test_invalid_medication_structure_error(self) -> None:
        assert isinstance(InvalidMedicationStructureError("x"), DomainError)

    def test_duplicate_medication_error(self) -> None:
        assert isinstance(DuplicateMedicationError("x"), DomainError)

    def test_missing_medication_dosage_error(self) -> None:
        assert isinstance(MissingMedicationDosageError("x"), DomainError)

    def test_missing_medication_frequency_error(self) -> None:
        assert isinstance(MissingMedicationFrequencyError("x"), DomainError)

    def test_missing_medication_duration_error(self) -> None:
        assert isinstance(MissingMedicationDurationError("x"), DomainError)

    def test_hallucinated_medication_error(self) -> None:
        assert isinstance(HallucinatedMedicationError("x", "y"), DomainError)
