"""Tests for the AI Risk Stratification & Early Warning Score module's
domain exceptions — message content and attribute preservation."""

from app.modules.risk_stratification_ai.domain.exceptions import (
    HallucinatedRiskFactorError,
    IncompleteLaboratoryValueError,
    InvalidRiskConfidenceValueError,
    InvalidRiskScoreError,
    InvalidRiskStratificationInputError,
    InvalidRiskStratificationResponseFormatError,
    MissingVitalSignsError,
)
from app.shared.domain.exceptions import DomainError


class TestInvalidRiskStratificationInputError:
    def test_is_domain_error(self) -> None:
        assert isinstance(InvalidRiskStratificationInputError("bad"), DomainError)

    def test_message_includes_reason(self) -> None:
        error = InvalidRiskStratificationInputError("patient_age must be non-negative")
        assert "patient_age must be non-negative" in str(error)

    def test_stores_reason_attribute(self) -> None:
        error = InvalidRiskStratificationInputError("bad")
        assert error.reason == "bad"


class TestMissingVitalSignsError:
    def test_is_domain_error(self) -> None:
        assert isinstance(MissingVitalSignsError(), DomainError)

    def test_message(self) -> None:
        assert "at least one vital sign" in str(MissingVitalSignsError())


class TestIncompleteLaboratoryValueError:
    def test_is_domain_error(self) -> None:
        assert isinstance(IncompleteLaboratoryValueError("Creatinine"), DomainError)

    def test_message_includes_test_name(self) -> None:
        error = IncompleteLaboratoryValueError("Creatinine")
        assert "Creatinine" in str(error)
        assert "reported value" in str(error)
        assert "numeric value" in str(error)

    def test_stores_test_name_attribute(self) -> None:
        error = IncompleteLaboratoryValueError("Creatinine")
        assert error.test_name == "Creatinine"


class TestInvalidRiskStratificationResponseFormatError:
    def test_is_domain_error(self) -> None:
        assert isinstance(InvalidRiskStratificationResponseFormatError("bad"), DomainError)

    def test_message_includes_reason(self) -> None:
        error = InvalidRiskStratificationResponseFormatError("no JSON object found")
        assert "no JSON object found" in str(error)


class TestInvalidRiskScoreError:
    def test_is_domain_error(self) -> None:
        assert isinstance(InvalidRiskScoreError("news2", 99.0), DomainError)

    def test_message_includes_category_and_value(self) -> None:
        error = InvalidRiskScoreError("news2", 99.0)
        assert "news2" in str(error)
        assert "99.0" in str(error)

    def test_stores_attributes(self) -> None:
        error = InvalidRiskScoreError("news2", 99.0)
        assert error.category == "news2"
        assert error.score_value == 99.0


class TestHallucinatedRiskFactorError:
    def test_is_domain_error(self) -> None:
        error = HallucinatedRiskFactorError("clinical_reasoning", "[insert]")
        assert isinstance(error, DomainError)

    def test_message_includes_field_and_placeholder(self) -> None:
        error = HallucinatedRiskFactorError("clinical_reasoning", "[insert]")
        assert "clinical_reasoning" in str(error)
        assert "[insert]" in str(error)

    def test_stores_attributes(self) -> None:
        error = HallucinatedRiskFactorError("clinical_reasoning", "[insert]")
        assert error.field_name == "clinical_reasoning"
        assert error.placeholder == "[insert]"


class TestInvalidRiskConfidenceValueError:
    def test_is_domain_error(self) -> None:
        assert isinstance(InvalidRiskConfidenceValueError(), DomainError)

    def test_message(self) -> None:
        assert "confidence_score" in str(InvalidRiskConfidenceValueError())
