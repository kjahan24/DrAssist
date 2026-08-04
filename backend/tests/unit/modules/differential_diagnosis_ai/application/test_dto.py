"""Unit tests for the AI Differential Diagnosis module's application
DTOs."""

from app.modules.differential_diagnosis_ai.application.dto import (
    ClinicalEvidenceValidationResultDTO,
    GeneratedDifferentialDiagnosis,
)
from tests.unit.modules.differential_diagnosis_ai.application.fakes import (
    make_generation_session,
    make_result,
)


class TestGeneratedDifferentialDiagnosis:
    def test_bundles_result_and_session(self) -> None:
        result = make_result()
        session = make_generation_session()

        generated = GeneratedDifferentialDiagnosis(result=result, session=session)

        assert generated.result is result
        assert generated.session is session


class TestClinicalEvidenceValidationResultDTO:
    def test_defaults_errors_and_warnings_to_empty(self) -> None:
        result = ClinicalEvidenceValidationResultDTO(is_valid=True)
        assert result.errors == ()
        assert result.warnings == ()

    def test_accepts_errors_and_warnings(self) -> None:
        result = ClinicalEvidenceValidationResultDTO(
            is_valid=False, errors=("bad",), warnings=("meh",)
        )
        assert result.is_valid is False
        assert result.errors == ("bad",)
        assert result.warnings == ("meh",)
