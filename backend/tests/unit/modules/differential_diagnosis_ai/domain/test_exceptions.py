"""Unit tests for the AI Differential Diagnosis module's domain
exceptions."""

from app.modules.differential_diagnosis_ai.domain.exceptions import (
    DuplicateDiagnosisError,
    EmptyDifferentialResponseError,
    HallucinatedDiagnosisError,
    InconsistentReasoningError,
    InvalidClinicalEvidenceError,
    InvalidConfidenceScoreError,
    InvalidDifferentialResponseFormatError,
    InvalidRankingError,
)
from app.shared.domain.exceptions import DomainError


class TestInvalidClinicalEvidenceError:
    def test_message_includes_reason(self) -> None:
        exc = InvalidClinicalEvidenceError("chief_complaint must not be blank")
        assert "chief_complaint must not be blank" in str(exc)
        assert exc.reason == "chief_complaint must not be blank"


class TestInvalidDifferentialResponseFormatError:
    def test_message_includes_reason(self) -> None:
        exc = InvalidDifferentialResponseFormatError("malformed JSON")
        assert "malformed JSON" in str(exc)
        assert exc.reason == "malformed JSON"


class TestEmptyDifferentialResponseError:
    def test_has_a_stable_message(self) -> None:
        assert "no differential diagnosis candidates" in str(EmptyDifferentialResponseError())


class TestDuplicateDiagnosisError:
    def test_message_includes_the_disease_name(self) -> None:
        exc = DuplicateDiagnosisError("Pneumonia")
        assert "Pneumonia" in str(exc)
        assert exc.disease_name == "Pneumonia"


class TestHallucinatedDiagnosisError:
    def test_message_includes_name_and_placeholder(self) -> None:
        exc = HallucinatedDiagnosisError("Pneumonia", "[INSERT REASONING]")
        assert "Pneumonia" in str(exc)
        assert "[INSERT REASONING]" in str(exc)
        assert exc.disease_name == "Pneumonia"
        assert exc.placeholder == "[INSERT REASONING]"


class TestInvalidConfidenceScoreError:
    def test_message_includes_the_disease_name(self) -> None:
        exc = InvalidConfidenceScoreError("Pneumonia")
        assert "Pneumonia" in str(exc)
        assert exc.disease_name == "Pneumonia"


class TestInvalidRankingError:
    def test_message_includes_reason(self) -> None:
        exc = InvalidRankingError("out of order")
        assert "out of order" in str(exc)
        assert exc.reason == "out of order"


class TestInconsistentReasoningError:
    def test_message_includes_name_and_reason(self) -> None:
        exc = InconsistentReasoningError("Pneumonia", "overlapping findings")
        assert "Pneumonia" in str(exc)
        assert "overlapping findings" in str(exc)
        assert exc.disease_name == "Pneumonia"
        assert exc.reason == "overlapping findings"


class TestAllDomainExceptionsAreDomainErrors:
    def test_invalid_clinical_evidence_error(self) -> None:
        assert isinstance(InvalidClinicalEvidenceError("x"), DomainError)

    def test_invalid_differential_response_format_error(self) -> None:
        assert isinstance(InvalidDifferentialResponseFormatError("x"), DomainError)

    def test_empty_differential_response_error(self) -> None:
        assert isinstance(EmptyDifferentialResponseError(), DomainError)

    def test_duplicate_diagnosis_error(self) -> None:
        assert isinstance(DuplicateDiagnosisError("x"), DomainError)

    def test_hallucinated_diagnosis_error(self) -> None:
        assert isinstance(HallucinatedDiagnosisError("x", "y"), DomainError)

    def test_invalid_confidence_score_error(self) -> None:
        assert isinstance(InvalidConfidenceScoreError("x"), DomainError)

    def test_invalid_ranking_error(self) -> None:
        assert isinstance(InvalidRankingError("x"), DomainError)

    def test_inconsistent_reasoning_error(self) -> None:
        assert isinstance(InconsistentReasoningError("x", "y"), DomainError)
