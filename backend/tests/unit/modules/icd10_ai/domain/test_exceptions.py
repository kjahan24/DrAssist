"""Unit tests for the AI ICD-10 Coding module's domain exceptions."""

from app.modules.icd10_ai.domain.exceptions import (
    DuplicateICD10CodeError,
    EmptyICD10ResponseError,
    HallucinatedDiagnosisError,
    InvalidClinicalContextError,
    InvalidICD10CodeError,
    InvalidICD10ResponseFormatError,
    MissingConfidenceScoreError,
)
from app.shared.domain.exceptions import DomainError


class TestInvalidClinicalContextError:
    def test_message_includes_reason(self) -> None:
        exc = InvalidClinicalContextError("chief_complaint must not be blank")
        assert "chief_complaint must not be blank" in str(exc)
        assert exc.reason == "chief_complaint must not be blank"


class TestInvalidICD10ResponseFormatError:
    def test_message_includes_reason(self) -> None:
        exc = InvalidICD10ResponseFormatError("malformed JSON")
        assert "malformed JSON" in str(exc)
        assert exc.reason == "malformed JSON"


class TestEmptyICD10ResponseError:
    def test_has_a_stable_message(self) -> None:
        assert "no ICD-10 suggestions" in str(EmptyICD10ResponseError())


class TestInvalidICD10CodeError:
    def test_message_includes_the_code(self) -> None:
        exc = InvalidICD10CodeError("NOT-A-CODE")
        assert "NOT-A-CODE" in str(exc)
        assert exc.icd10_code == "NOT-A-CODE"


class TestDuplicateICD10CodeError:
    def test_message_includes_the_code(self) -> None:
        exc = DuplicateICD10CodeError("J06.9")
        assert "J06.9" in str(exc)
        assert exc.icd10_code == "J06.9"


class TestHallucinatedDiagnosisError:
    def test_message_includes_code_and_placeholder(self) -> None:
        exc = HallucinatedDiagnosisError("J06.9", "[INSERT DIAGNOSIS]")
        assert "J06.9" in str(exc)
        assert "[INSERT DIAGNOSIS]" in str(exc)
        assert exc.icd10_code == "J06.9"
        assert exc.placeholder == "[INSERT DIAGNOSIS]"


class TestMissingConfidenceScoreError:
    def test_message_includes_the_code(self) -> None:
        exc = MissingConfidenceScoreError("J06.9")
        assert "J06.9" in str(exc)
        assert exc.icd10_code == "J06.9"


class TestAllDomainExceptionsAreDomainErrors:
    def test_invalid_clinical_context_error(self) -> None:
        assert isinstance(InvalidClinicalContextError("x"), DomainError)

    def test_invalid_icd10_response_format_error(self) -> None:
        assert isinstance(InvalidICD10ResponseFormatError("x"), DomainError)

    def test_empty_icd10_response_error(self) -> None:
        assert isinstance(EmptyICD10ResponseError(), DomainError)

    def test_invalid_icd10_code_error(self) -> None:
        assert isinstance(InvalidICD10CodeError("x"), DomainError)

    def test_duplicate_icd10_code_error(self) -> None:
        assert isinstance(DuplicateICD10CodeError("x"), DomainError)

    def test_hallucinated_diagnosis_error(self) -> None:
        assert isinstance(HallucinatedDiagnosisError("x", "y"), DomainError)

    def test_missing_confidence_score_error(self) -> None:
        assert isinstance(MissingConfidenceScoreError("x"), DomainError)
