"""Unit tests for `DefaultMedicalReasoningValidator`."""

import pytest

from app.modules.medical_reasoning_ai.application.services.evidence_analysis_service import (
    EvidenceAnalysisService,
)
from app.modules.medical_reasoning_ai.application.services.recommendation_reasoning_service import (
    RecommendationReasoningService,
)
from app.modules.medical_reasoning_ai.domain.enums import EvidencePolarity, RedFlagPriority
from app.modules.medical_reasoning_ai.domain.exceptions import (
    DuplicateEvidenceError,
    EmptyReasoningResponseError,
    HallucinatedReasoningPlaceholderError,
    InconsistentRecommendationsError,
    InvalidConfidenceValueError,
    MissingReasoningError,
)
from app.modules.medical_reasoning_ai.domain.value_objects import RedFlag
from app.modules.medical_reasoning_ai.infrastructure.validation.medical_reasoning_validator import (
    DefaultMedicalReasoningValidator,
)
from tests.unit.modules.medical_reasoning_ai.application.fakes import (
    FakeEvidenceAnalyzerPort,
    make_evidence_item,
    make_result,
)


def _validator() -> DefaultMedicalReasoningValidator:
    return DefaultMedicalReasoningValidator(
        evidence_service=EvidenceAnalysisService(analyzer=FakeEvidenceAnalyzerPort()),
        recommendation_service=RecommendationReasoningService(),
    )


class TestValidateHappyPath:
    def test_accepts_a_well_formed_result(self) -> None:
        _validator().validate(make_result())


class TestValidateEmptyResponse:
    def test_raises_when_the_result_is_fully_vacuous(self) -> None:
        result = make_result(
            clinical_summary="",
            evidence=(),
            risk_factors=(),
            red_flags=(),
            suggested_next_questions=(),
            suggested_investigations=(),
            suggested_monitoring=(),
            clinical_justification="",
        )

        with pytest.raises(EmptyReasoningResponseError):
            _validator().validate(result)


class TestValidateMissingReasoning:
    def test_raises_when_clinical_summary_is_blank(self) -> None:
        result = make_result(clinical_summary="")

        with pytest.raises(MissingReasoningError):
            _validator().validate(result)

    def test_raises_when_justification_is_blank_but_evidence_was_reported(self) -> None:
        result = make_result(clinical_justification="")

        with pytest.raises(MissingReasoningError):
            _validator().validate(result)

    def test_accepts_blank_justification_when_nothing_else_was_reported(self) -> None:
        result = make_result(
            evidence=(),
            risk_factors=(),
            red_flags=(),
            suggested_next_questions=(),
            suggested_investigations=(),
            suggested_monitoring=(),
            clinical_justification="",
        )

        _validator().validate(result)


class TestValidateDuplicateEvidence:
    def test_raises_when_the_same_description_appears_twice(self) -> None:
        result = make_result(
            evidence=(
                make_evidence_item(description="Fever present"),
                make_evidence_item(description="Fever present"),
            )
        )

        with pytest.raises(DuplicateEvidenceError) as exc_info:
            _validator().validate(result)
        assert exc_info.value.description == "Fever present"

    def test_does_not_flag_genuinely_different_evidence(self) -> None:
        result = make_result(
            evidence=(
                make_evidence_item(description="Fever present"),
                make_evidence_item(description="Productive cough"),
            )
        )

        _validator().validate(result)


class TestValidateInvalidConfidenceValues:
    @pytest.mark.parametrize("confidence_score", [-0.1, 1.1, -5.0, 100.0])
    def test_raises_when_clinical_confidence_is_out_of_range(self, confidence_score: float) -> None:
        result = make_result(clinical_confidence=confidence_score)

        with pytest.raises(InvalidConfidenceValueError) as exc_info:
            _validator().validate(result)
        assert exc_info.value.dimension == "clinical"

    def test_accepts_a_none_confidence_value(self) -> None:
        result = make_result(clinical_confidence=None)

        _validator().validate(result)

    @pytest.mark.parametrize("confidence_score", [0.0, 1.0, 0.5])
    def test_accepts_boundary_valid_confidence_scores(self, confidence_score: float) -> None:
        result = make_result(diagnostic_confidence=confidence_score)

        _validator().validate(result)


class TestValidateHallucinatedPlaceholders:
    @pytest.mark.parametrize(
        "placeholder",
        [
            "[insert summary here]",
            "[PLACEHOLDER]",
            "<insert findings>",
            "TBD",
            "TODO",
            "XXX",
            "Lorem ipsum dolor sit amet",
        ],
    )
    def test_raises_when_clinical_summary_contains_a_placeholder(self, placeholder: str) -> None:
        result = make_result(clinical_summary=f"Summary: {placeholder}")

        with pytest.raises(HallucinatedReasoningPlaceholderError) as exc_info:
            _validator().validate(result)
        assert exc_info.value.field_name == "clinical_summary"

    def test_raises_when_clinical_justification_contains_a_placeholder(self) -> None:
        result = make_result(clinical_justification="Justification: TBD")

        with pytest.raises(HallucinatedReasoningPlaceholderError):
            _validator().validate(result)

    def test_raises_when_an_evidence_description_contains_a_placeholder(self) -> None:
        result = make_result(evidence=(make_evidence_item(description="[insert finding]"),))

        with pytest.raises(HallucinatedReasoningPlaceholderError):
            _validator().validate(result)

    def test_raises_when_a_risk_factor_contains_a_placeholder(self) -> None:
        result = make_result(risk_factors=("TBD",))

        with pytest.raises(HallucinatedReasoningPlaceholderError):
            _validator().validate(result)

    def test_raises_when_a_red_flag_description_contains_a_placeholder(self) -> None:
        result = make_result(
            red_flags=(RedFlag(description="[insert red flag]", priority=RedFlagPriority.HIGH),)
        )

        with pytest.raises(HallucinatedReasoningPlaceholderError):
            _validator().validate(result)

    def test_does_not_flag_ordinary_clinical_language(self) -> None:
        _validator().validate(make_result())


class TestValidateInconsistentRecommendations:
    def test_raises_when_suggested_investigations_has_a_duplicate(self) -> None:
        result = make_result(suggested_investigations=("CBC", "CBC"))

        with pytest.raises(InconsistentRecommendationsError) as exc_info:
            _validator().validate(result)
        assert exc_info.value.list_name == "suggested_investigations"
        assert exc_info.value.item == "CBC"

    def test_raises_when_suggested_next_questions_has_a_duplicate(self) -> None:
        result = make_result(suggested_next_questions=("Any recent travel?", "Any recent travel?"))

        with pytest.raises(InconsistentRecommendationsError) as exc_info:
            _validator().validate(result)
        assert exc_info.value.list_name == "suggested_next_questions"

    def test_raises_when_suggested_monitoring_has_a_duplicate(self) -> None:
        result = make_result(suggested_monitoring=("Repeat troponin", "repeat troponin"))

        with pytest.raises(InconsistentRecommendationsError) as exc_info:
            _validator().validate(result)
        assert exc_info.value.list_name == "suggested_monitoring"

    def test_does_not_flag_the_same_item_across_different_lists(self) -> None:
        result = make_result(
            suggested_investigations=("CBC",),
            suggested_monitoring=("CBC",),
        )

        _validator().validate(result)


class TestValidateCheckOrdering:
    def test_missing_reasoning_is_checked_before_duplicate_evidence(self) -> None:
        """A blank clinical_summary combined with duplicate evidence must
        raise `MissingReasoningError`, not `DuplicateEvidenceError` —
        confirms missing-reasoning is checked first."""
        result = make_result(
            clinical_summary="",
            evidence=(
                make_evidence_item(description="Fever"),
                make_evidence_item(description="Fever"),
            ),
        )

        with pytest.raises(MissingReasoningError):
            _validator().validate(result)

    def test_evidence_polarity_split_still_flags_duplicates(self) -> None:
        result = make_result(
            evidence=(
                make_evidence_item(description="Fever", polarity=EvidencePolarity.SUPPORTING),
                make_evidence_item(description="Fever", polarity=EvidencePolarity.CONTRADICTING),
            )
        )

        with pytest.raises(DuplicateEvidenceError):
            _validator().validate(result)
