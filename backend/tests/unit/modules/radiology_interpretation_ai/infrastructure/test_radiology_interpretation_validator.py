"""Unit tests for `DefaultRadiologyInterpretationValidator`."""

import pytest

from app.modules.radiology_interpretation_ai.application.services.follow_up_recommendation_service import (  # noqa: E501
    FollowUpRecommendationService,
)
from app.modules.radiology_interpretation_ai.domain.exceptions import (
    DuplicateRadiologyFindingError,
    HallucinatedRadiologyFindingError,
    InconsistentRadiologyRecommendationsError,
    InvalidRadiologyConfidenceValueError,
)
from app.modules.radiology_interpretation_ai.infrastructure.validation.radiology_interpretation_validator import (  # noqa: E501
    DefaultRadiologyInterpretationValidator,
)
from tests.unit.modules.radiology_interpretation_ai.application.fakes import (
    make_finding,
    make_result,
)


def _validator() -> DefaultRadiologyInterpretationValidator:
    return DefaultRadiologyInterpretationValidator(
        recommendation_service=FollowUpRecommendationService()
    )


class TestValidateHappyPath:
    def test_accepts_a_well_formed_result(self) -> None:
        _validator().validate(make_result())


class TestValidateDuplicateFindings:
    def test_raises_when_the_same_description_appears_twice(self) -> None:
        result = make_result(
            findings=(
                make_finding(description="Pneumothorax"),
                make_finding(description="Pneumothorax"),
            )
        )

        with pytest.raises(DuplicateRadiologyFindingError) as exc_info:
            _validator().validate(result)
        assert exc_info.value.description == "Pneumothorax"

    def test_is_case_insensitive(self) -> None:
        result = make_result(
            findings=(
                make_finding(description="Pneumothorax"),
                make_finding(description="pneumothorax"),
            )
        )

        with pytest.raises(DuplicateRadiologyFindingError):
            _validator().validate(result)

    def test_does_not_flag_genuinely_different_findings(self) -> None:
        result = make_result(
            findings=(
                make_finding(description="Pneumothorax"),
                make_finding(description="Small pleural effusion"),
            )
        )

        _validator().validate(result)


class TestValidateInvalidConfidenceValues:
    @pytest.mark.parametrize("confidence_score", [-0.1, 1.1, -5.0, 100.0])
    def test_raises_when_confidence_is_out_of_range(self, confidence_score: float) -> None:
        result = make_result(confidence_score=confidence_score)

        with pytest.raises(InvalidRadiologyConfidenceValueError):
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
    def test_raises_when_examination_summary_contains_a_placeholder(self, placeholder: str) -> None:
        result = make_result(examination_summary=f"Summary: {placeholder}")

        with pytest.raises(HallucinatedRadiologyFindingError) as exc_info:
            _validator().validate(result)
        assert exc_info.value.field_name == "examination_summary"

    def test_raises_when_clinical_significance_contains_a_placeholder(self) -> None:
        result = make_result(clinical_significance="Significance: TBD")

        with pytest.raises(HallucinatedRadiologyFindingError):
            _validator().validate(result)

    def test_raises_when_clinical_reasoning_contains_a_placeholder(self) -> None:
        result = make_result(clinical_reasoning="Reasoning: TBD")

        with pytest.raises(HallucinatedRadiologyFindingError):
            _validator().validate(result)

    def test_raises_when_a_finding_description_contains_a_placeholder(self) -> None:
        result = make_result(findings=(make_finding(description="[insert finding]"),))

        with pytest.raises(HallucinatedRadiologyFindingError) as exc_info:
            _validator().validate(result)
        assert exc_info.value.field_name == "findings"

    def test_raises_when_a_red_flag_warning_contains_a_placeholder(self) -> None:
        result = make_result(red_flag_warnings=("[insert warning]",))

        with pytest.raises(HallucinatedRadiologyFindingError) as exc_info:
            _validator().validate(result)
        assert exc_info.value.field_name == "red_flag_warnings"

    def test_does_not_flag_ordinary_clinical_language(self) -> None:
        _validator().validate(make_result())


class TestValidateInconsistentRecommendations:
    def test_raises_when_differential_imaging_considerations_has_a_duplicate(self) -> None:
        result = make_result(differential_imaging_considerations=("Possible mass", "Possible mass"))

        with pytest.raises(InconsistentRadiologyRecommendationsError) as exc_info:
            _validator().validate(result)
        assert exc_info.value.list_name == "differential_imaging_considerations"
        assert exc_info.value.item == "Possible mass"

    def test_raises_when_suggested_follow_up_imaging_has_a_duplicate(self) -> None:
        result = make_result(suggested_follow_up_imaging=("Repeat CT", "repeat CT"))

        with pytest.raises(InconsistentRadiologyRecommendationsError) as exc_info:
            _validator().validate(result)
        assert exc_info.value.list_name == "suggested_follow_up_imaging"

    def test_raises_when_suggested_specialist_referral_has_a_duplicate(self) -> None:
        result = make_result(suggested_specialist_referral=("Thoracic surgery", "thoracic surgery"))

        with pytest.raises(InconsistentRadiologyRecommendationsError) as exc_info:
            _validator().validate(result)
        assert exc_info.value.list_name == "suggested_specialist_referral"

    def test_does_not_flag_the_same_item_across_different_lists(self) -> None:
        result = make_result(
            suggested_follow_up_imaging=("Repeat CT",),
            suggested_specialist_referral=("Repeat CT",),
        )

        _validator().validate(result)


class TestValidateCheckOrdering:
    def test_duplicate_findings_is_checked_before_confidence_value(self) -> None:
        result = make_result(
            findings=(
                make_finding(description="Pneumothorax"),
                make_finding(description="Pneumothorax"),
            ),
            confidence_score=5.0,
        )

        with pytest.raises(DuplicateRadiologyFindingError):
            _validator().validate(result)
