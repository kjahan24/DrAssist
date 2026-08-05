"""Unit tests for `DefaultPathologyInterpretationValidator`."""

import pytest

from app.modules.pathology_interpretation_ai.application.services.clinical_correlation_service import (  # noqa: E501
    ClinicalCorrelationService,
)
from app.modules.pathology_interpretation_ai.domain.exceptions import (
    DuplicatePathologyFindingError,
    HallucinatedPathologyFindingError,
    InconsistentPathologyConclusionsError,
    InvalidPathologyConfidenceValueError,
)
from app.modules.pathology_interpretation_ai.infrastructure.validation.pathology_interpretation_validator import (  # noqa: E501
    DefaultPathologyInterpretationValidator,
)
from tests.unit.modules.pathology_interpretation_ai.application.fakes import (
    make_finding,
    make_result,
)


def _validator() -> DefaultPathologyInterpretationValidator:
    return DefaultPathologyInterpretationValidator(correlation_service=ClinicalCorrelationService())


class TestValidateHappyPath:
    def test_accepts_a_well_formed_result(self) -> None:
        _validator().validate(make_result())


class TestValidateDuplicateFindings:
    def test_raises_when_the_same_description_appears_twice(self) -> None:
        result = make_result(
            microscopic_findings=(
                make_finding(description="Carcinoma"),
                make_finding(description="Carcinoma"),
            )
        )

        with pytest.raises(DuplicatePathologyFindingError) as exc_info:
            _validator().validate(result)
        assert exc_info.value.description == "Carcinoma"

    def test_is_case_insensitive(self) -> None:
        result = make_result(
            microscopic_findings=(
                make_finding(description="Carcinoma"),
                make_finding(description="carcinoma"),
            )
        )

        with pytest.raises(DuplicatePathologyFindingError):
            _validator().validate(result)

    def test_does_not_flag_genuinely_different_findings(self) -> None:
        result = make_result(
            microscopic_findings=(
                make_finding(description="Carcinoma"),
                make_finding(description="Reactive changes"),
            )
        )

        _validator().validate(result)


class TestValidateInvalidConfidenceValues:
    @pytest.mark.parametrize("confidence_score", [-0.1, 1.1, -5.0, 100.0])
    def test_raises_when_confidence_is_out_of_range(self, confidence_score: float) -> None:
        result = make_result(confidence_score=confidence_score)

        with pytest.raises(InvalidPathologyConfidenceValueError):
            _validator().validate(result)

    def test_accepts_a_none_confidence_value(self) -> None:
        result = make_result(confidence_score=None)
        _validator().validate(result)

    @pytest.mark.parametrize("confidence_score", [0.0, 1.0, 0.5])
    def test_accepts_boundary_valid_confidence_scores(self, confidence_score: float) -> None:
        result = make_result(confidence_score=confidence_score)
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
    def test_raises_when_pathology_summary_contains_a_placeholder(self, placeholder: str) -> None:
        result = make_result(pathology_summary=f"Summary: {placeholder}")

        with pytest.raises(HallucinatedPathologyFindingError) as exc_info:
            _validator().validate(result)
        assert exc_info.value.field_name == "pathology_summary"

    def test_raises_when_final_impression_contains_a_placeholder(self) -> None:
        result = make_result(final_impression="Impression: TBD")

        with pytest.raises(HallucinatedPathologyFindingError):
            _validator().validate(result)

    def test_raises_when_clinical_significance_contains_a_placeholder(self) -> None:
        result = make_result(clinical_significance="Significance: TBD")

        with pytest.raises(HallucinatedPathologyFindingError):
            _validator().validate(result)

    def test_raises_when_clinical_reasoning_contains_a_placeholder(self) -> None:
        result = make_result(clinical_reasoning="Reasoning: TBD")

        with pytest.raises(HallucinatedPathologyFindingError):
            _validator().validate(result)

    def test_raises_when_a_finding_description_contains_a_placeholder(self) -> None:
        result = make_result(microscopic_findings=(make_finding(description="[insert finding]"),))

        with pytest.raises(HallucinatedPathologyFindingError) as exc_info:
            _validator().validate(result)
        assert exc_info.value.field_name == "microscopic_findings"

    def test_raises_when_a_red_flag_warning_contains_a_placeholder(self) -> None:
        result = make_result(red_flag_warnings=("[insert warning]",))

        with pytest.raises(HallucinatedPathologyFindingError) as exc_info:
            _validator().validate(result)
        assert exc_info.value.field_name == "red_flag_warnings"

    def test_raises_when_a_key_finding_contains_a_placeholder(self) -> None:
        result = make_result(key_findings=("[insert key finding]",))

        with pytest.raises(HallucinatedPathologyFindingError) as exc_info:
            _validator().validate(result)
        assert exc_info.value.field_name == "key_findings"

    def test_does_not_flag_ordinary_clinical_language(self) -> None:
        _validator().validate(make_result())


class TestValidateInconsistentConclusions:
    def test_raises_when_correlation_recommendations_has_a_duplicate(self) -> None:
        result = make_result(correlation_recommendations=("IHC panel", "IHC panel"))

        with pytest.raises(InconsistentPathologyConclusionsError) as exc_info:
            _validator().validate(result)
        assert exc_info.value.list_name == "correlation_recommendations"
        assert exc_info.value.item == "IHC panel"

    def test_raises_when_suggested_follow_up_has_a_duplicate(self) -> None:
        result = make_result(suggested_follow_up=("Repeat biopsy", "repeat biopsy"))

        with pytest.raises(InconsistentPathologyConclusionsError) as exc_info:
            _validator().validate(result)
        assert exc_info.value.list_name == "suggested_follow_up"

    def test_raises_when_suggested_specialist_referral_has_a_duplicate(self) -> None:
        result = make_result(suggested_specialist_referral=("Oncology", "oncology"))

        with pytest.raises(InconsistentPathologyConclusionsError) as exc_info:
            _validator().validate(result)
        assert exc_info.value.list_name == "suggested_specialist_referral"

    def test_does_not_flag_the_same_item_across_different_lists(self) -> None:
        result = make_result(
            suggested_follow_up=("Repeat biopsy",),
            suggested_specialist_referral=("Repeat biopsy",),
        )

        _validator().validate(result)


class TestValidateCheckOrdering:
    def test_duplicate_findings_is_checked_before_confidence_value(self) -> None:
        result = make_result(
            microscopic_findings=(
                make_finding(description="Carcinoma"),
                make_finding(description="Carcinoma"),
            ),
            confidence_score=5.0,
        )

        with pytest.raises(DuplicatePathologyFindingError):
            _validator().validate(result)
