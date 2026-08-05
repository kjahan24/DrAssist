"""Unit tests for the AI Drug Interaction & Medication Safety module's
domain exceptions."""

from app.modules.drug_interaction_ai.domain.exceptions import (
    DuplicateMedicationError,
    EmptyMedicationListError,
    HallucinatedInteractionError,
    InvalidDrugInteractionConfidenceValueError,
    InvalidDrugInteractionInputError,
    InvalidDrugInteractionResponseFormatError,
    MissingInteractionEvidenceError,
    UnknownMedicationError,
)
from app.shared.domain.exceptions import DomainError


class TestInvalidDrugInteractionInputError:
    def test_carries_the_reason(self) -> None:
        error = InvalidDrugInteractionInputError("language must not be blank")
        assert error.reason == "language must not be blank"
        assert "language must not be blank" in str(error)
        assert isinstance(error, DomainError)


class TestEmptyMedicationListError:
    def test_is_a_domain_error(self) -> None:
        error = EmptyMedicationListError()
        assert isinstance(error, DomainError)
        assert "current_medications" in str(error)


class TestDuplicateMedicationError:
    def test_carries_the_drug_name(self) -> None:
        error = DuplicateMedicationError("Warfarin")
        assert error.drug_name == "Warfarin"
        assert "Warfarin" in str(error)


class TestInvalidDrugInteractionResponseFormatError:
    def test_carries_the_reason(self) -> None:
        error = InvalidDrugInteractionResponseFormatError("not valid JSON")
        assert error.reason == "not valid JSON"


class TestUnknownMedicationError:
    def test_carries_the_medication_name(self) -> None:
        error = UnknownMedicationError("Ibuprofen")
        assert error.medication_name == "Ibuprofen"
        assert "Ibuprofen" in str(error)


class TestHallucinatedInteractionError:
    def test_carries_the_field_name_and_placeholder(self) -> None:
        error = HallucinatedInteractionError("safety_summary", "[insert]")
        assert error.field_name == "safety_summary"
        assert error.placeholder == "[insert]"


class TestInvalidDrugInteractionConfidenceValueError:
    def test_is_a_domain_error(self) -> None:
        error = InvalidDrugInteractionConfidenceValueError()
        assert isinstance(error, DomainError)
        assert "confidence_score" in str(error)


class TestMissingInteractionEvidenceError:
    def test_carries_the_description(self) -> None:
        error = MissingInteractionEvidenceError("Warfarin and Aspirin interaction")
        assert error.description == "Warfarin and Aspirin interaction"
        assert "Warfarin and Aspirin interaction" in str(error)
