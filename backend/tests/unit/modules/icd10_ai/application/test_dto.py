"""Unit tests for the AI ICD-10 Coding module's application DTOs."""

from app.modules.icd10_ai.application.dto import (
    ClinicalContextValidationResultDTO,
    GeneratedICD10Suggestions,
)
from tests.unit.modules.icd10_ai.application.fakes import (
    make_generation_session,
    make_suggestion_set,
)


class TestGeneratedICD10Suggestions:
    def test_bundles_suggestions_and_session(self) -> None:
        suggestions = make_suggestion_set()
        session = make_generation_session()

        result = GeneratedICD10Suggestions(suggestions=suggestions, session=session)

        assert result.suggestions is suggestions
        assert result.session is session


class TestClinicalContextValidationResultDTO:
    def test_defaults_errors_and_warnings_to_empty(self) -> None:
        result = ClinicalContextValidationResultDTO(is_valid=True)
        assert result.errors == ()
        assert result.warnings == ()

    def test_accepts_errors_and_warnings(self) -> None:
        result = ClinicalContextValidationResultDTO(
            is_valid=False, errors=("bad",), warnings=("meh",)
        )
        assert result.is_valid is False
        assert result.errors == ("bad",)
        assert result.warnings == ("meh",)
