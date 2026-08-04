"""Unit tests for the AI Prescription Assistance module's application
DTOs."""

from app.modules.prescription_ai.application.dto import (
    GeneratedPrescriptionSuggestions,
    MedicationSafetyAnalysisInput,
    PrescriptionContextValidationResultDTO,
)
from tests.unit.modules.prescription_ai.application.fakes import (
    make_generation_session,
    make_medication,
    make_suggestion_set,
)


class TestGeneratedPrescriptionSuggestions:
    def test_bundles_suggestions_and_session(self) -> None:
        suggestions = make_suggestion_set()
        session = make_generation_session()

        result = GeneratedPrescriptionSuggestions(suggestions=suggestions, session=session)

        assert result.suggestions is suggestions
        assert result.session is session


class TestPrescriptionContextValidationResultDTO:
    def test_defaults_errors_and_warnings_to_empty(self) -> None:
        result = PrescriptionContextValidationResultDTO(is_valid=True)
        assert result.errors == ()
        assert result.warnings == ()

    def test_accepts_errors_and_warnings(self) -> None:
        result = PrescriptionContextValidationResultDTO(
            is_valid=False, errors=("bad",), warnings=("meh",)
        )
        assert result.is_valid is False
        assert result.errors == ("bad",)
        assert result.warnings == ("meh",)


class TestMedicationSafetyAnalysisInput:
    def test_defaults_existing_medications_and_allergies_to_empty(self) -> None:
        result = MedicationSafetyAnalysisInput(medications=(make_medication(),))
        assert result.existing_medications == ()
        assert result.allergies == ()

    def test_accepts_existing_medications_and_allergies(self) -> None:
        result = MedicationSafetyAnalysisInput(
            medications=(make_medication(),),
            existing_medications=("warfarin",),
            allergies=("penicillin",),
        )
        assert result.existing_medications == ("warfarin",)
        assert result.allergies == ("penicillin",)
