"""Unit tests for `DefaultPrescriptionSuggestionValidator`."""

import pytest

from app.modules.prescription_ai.domain.exceptions import (
    DuplicateMedicationError,
    EmptyPrescriptionResponseError,
    HallucinatedMedicationError,
    InvalidMedicationStructureError,
    MissingMedicationDosageError,
    MissingMedicationDurationError,
    MissingMedicationFrequencyError,
)
from app.modules.prescription_ai.infrastructure.validation import (
    prescription_suggestion_validator,
)
from tests.unit.modules.prescription_ai.application.fakes import (
    make_medication,
    make_suggestion_set,
)


class TestValidateHappyPath:
    def test_accepts_a_well_formed_suggestion_set(self) -> None:
        validator = prescription_suggestion_validator.DefaultPrescriptionSuggestionValidator()
        validator.validate(make_suggestion_set())


class TestValidateEmptyResponse:
    def test_raises_when_there_are_no_medications(self) -> None:
        validator = prescription_suggestion_validator.DefaultPrescriptionSuggestionValidator()
        suggestion_set = make_suggestion_set(medications=())

        with pytest.raises(EmptyPrescriptionResponseError):
            validator.validate(suggestion_set)


class TestValidateInvalidStructure:
    def test_raises_when_generic_name_is_blank(self) -> None:
        validator = prescription_suggestion_validator.DefaultPrescriptionSuggestionValidator()
        suggestion_set = make_suggestion_set(medications=(make_medication(generic_name=""),))

        with pytest.raises(InvalidMedicationStructureError):
            validator.validate(suggestion_set)

    def test_raises_when_generic_name_is_whitespace_only(self) -> None:
        validator = prescription_suggestion_validator.DefaultPrescriptionSuggestionValidator()
        suggestion_set = make_suggestion_set(medications=(make_medication(generic_name="   "),))

        with pytest.raises(InvalidMedicationStructureError):
            validator.validate(suggestion_set)


class TestValidateDuplicateMedications:
    def test_raises_when_the_same_generic_name_appears_twice(self) -> None:
        validator = prescription_suggestion_validator.DefaultPrescriptionSuggestionValidator()
        suggestion_set = make_suggestion_set(
            medications=(
                make_medication(generic_name="ibuprofen"),
                make_medication(generic_name="ibuprofen"),
            )
        )

        with pytest.raises(DuplicateMedicationError) as exc_info:
            validator.validate(suggestion_set)
        assert exc_info.value.generic_name == "ibuprofen"

    def test_duplicate_detection_is_case_and_whitespace_insensitive(self) -> None:
        validator = prescription_suggestion_validator.DefaultPrescriptionSuggestionValidator()
        suggestion_set = make_suggestion_set(
            medications=(
                make_medication(generic_name="Ibuprofen"),
                make_medication(generic_name="  ibuprofen  "),
            )
        )

        with pytest.raises(DuplicateMedicationError):
            validator.validate(suggestion_set)

    def test_does_not_flag_genuinely_different_medications(self) -> None:
        validator = prescription_suggestion_validator.DefaultPrescriptionSuggestionValidator()
        suggestion_set = make_suggestion_set(
            medications=(
                make_medication(generic_name="ibuprofen"),
                make_medication(generic_name="amoxicillin"),
            )
        )

        validator.validate(suggestion_set)


class TestValidateMissingDosage:
    def test_raises_when_dosage_is_blank(self) -> None:
        validator = prescription_suggestion_validator.DefaultPrescriptionSuggestionValidator()
        suggestion_set = make_suggestion_set(medications=(make_medication(dosage=""),))

        with pytest.raises(MissingMedicationDosageError) as exc_info:
            validator.validate(suggestion_set)
        assert exc_info.value.generic_name == "amoxicillin"


class TestValidateMissingFrequency:
    def test_raises_when_frequency_is_blank(self) -> None:
        validator = prescription_suggestion_validator.DefaultPrescriptionSuggestionValidator()
        suggestion_set = make_suggestion_set(medications=(make_medication(frequency=""),))

        with pytest.raises(MissingMedicationFrequencyError):
            validator.validate(suggestion_set)


class TestValidateMissingDuration:
    def test_raises_when_duration_is_blank(self) -> None:
        validator = prescription_suggestion_validator.DefaultPrescriptionSuggestionValidator()
        suggestion_set = make_suggestion_set(medications=(make_medication(duration=""),))

        with pytest.raises(MissingMedicationDurationError):
            validator.validate(suggestion_set)


class TestValidateCheckOrdering:
    def test_structure_is_checked_before_required_fields(self) -> None:
        """A medication with both a blank generic_name and a blank
        dosage must raise the structure error, not the dosage error —
        confirms structure is checked first."""
        validator = prescription_suggestion_validator.DefaultPrescriptionSuggestionValidator()
        suggestion_set = make_suggestion_set(
            medications=(make_medication(generic_name="", dosage=""),)
        )

        with pytest.raises(InvalidMedicationStructureError):
            validator.validate(suggestion_set)

    def test_required_fields_are_checked_before_hallucination(self) -> None:
        validator = prescription_suggestion_validator.DefaultPrescriptionSuggestionValidator()
        suggestion_set = make_suggestion_set(
            medications=(make_medication(dosage="", clinical_reasoning="[INSERT REASONING]"),)
        )

        with pytest.raises(MissingMedicationDosageError):
            validator.validate(suggestion_set)


class TestValidateHallucinatedMedications:
    @pytest.mark.parametrize(
        "placeholder",
        [
            "[insert indication here]",
            "[PLACEHOLDER]",
            "<insert findings>",
            "TBD",
            "TODO",
            "XXX",
            "Lorem ipsum dolor sit amet",
        ],
    )
    def test_raises_when_clinical_indication_contains_a_placeholder(self, placeholder: str) -> None:
        validator = prescription_suggestion_validator.DefaultPrescriptionSuggestionValidator()
        suggestion_set = make_suggestion_set(
            medications=(make_medication(clinical_indication=f"Indication: {placeholder}"),)
        )

        with pytest.raises(HallucinatedMedicationError) as exc_info:
            validator.validate(suggestion_set)
        assert exc_info.value.generic_name == "amoxicillin"

    def test_raises_when_clinical_reasoning_contains_a_placeholder(self) -> None:
        validator = prescription_suggestion_validator.DefaultPrescriptionSuggestionValidator()
        suggestion_set = make_suggestion_set(
            medications=(make_medication(clinical_reasoning="Reasoning: TBD"),)
        )

        with pytest.raises(HallucinatedMedicationError):
            validator.validate(suggestion_set)

    def test_raises_when_monitoring_advice_contains_a_placeholder(self) -> None:
        validator = prescription_suggestion_validator.DefaultPrescriptionSuggestionValidator()
        suggestion_set = make_suggestion_set(
            medications=(make_medication(monitoring_advice="[insert monitoring]"),)
        )

        with pytest.raises(HallucinatedMedicationError):
            validator.validate(suggestion_set)

    def test_raises_when_patient_instructions_contains_a_placeholder(self) -> None:
        validator = prescription_suggestion_validator.DefaultPrescriptionSuggestionValidator()
        suggestion_set = make_suggestion_set(
            medications=(make_medication(patient_instructions="[insert instructions]"),)
        )

        with pytest.raises(HallucinatedMedicationError):
            validator.validate(suggestion_set)

    def test_does_not_flag_ordinary_clinical_language(self) -> None:
        validator = prescription_suggestion_validator.DefaultPrescriptionSuggestionValidator()
        validator.validate(make_suggestion_set())
