"""Unit tests for `DefaultPatientEducationAnalysisValidator`."""

import pytest

from app.modules.patient_education_ai.domain.exceptions import (
    HallucinatedRecommendationError,
    InvalidPatientEducationConfidenceValueError,
    UnsafeInstructionError,
)
from app.modules.patient_education_ai.infrastructure.validation.patient_education_validator import (  # noqa: E501
    DefaultPatientEducationAnalysisValidator,
)
from tests.unit.modules.patient_education_ai.application.fakes import make_input, make_result


def _validator() -> DefaultPatientEducationAnalysisValidator:
    return DefaultPatientEducationAnalysisValidator()


class TestValidateHappyPath:
    def test_accepts_a_well_formed_result(self) -> None:
        _validator().validate(make_result(), make_input())


class TestValidateUnsafeInstructions:
    @pytest.mark.parametrize(
        ("field_name", "phrase"),
        [
            ("medication_instructions", "double your dose"),
            ("home_care_plan", "stop all medications"),
            ("emergency_instructions", "no need to see a doctor"),
            ("warning_signs", "avoid the emergency room"),
        ],
    )
    def test_raises_when_a_checked_field_contains_an_unsafe_phrase(
        self, field_name: str, phrase: str
    ) -> None:
        result = make_result(**{field_name: (f"You should {phrase}.",)})

        with pytest.raises(UnsafeInstructionError) as exc_info:
            _validator().validate(result, make_input())
        assert exc_info.value.field_name == field_name

    def test_matches_case_insensitively(self) -> None:
        result = make_result(medication_instructions=("DOUBLE YOUR DOSE if needed.",))

        with pytest.raises(UnsafeInstructionError):
            _validator().validate(result, make_input())

    def test_does_not_flag_unrelated_fields(self) -> None:
        result = make_result(lifestyle_advice=("double your dose",))
        _validator().validate(result, make_input())

    def test_accepts_ordinary_medication_instructions(self) -> None:
        result = make_result(medication_instructions=("Take with food.",))
        _validator().validate(result, make_input())


class TestValidateInvalidConfidenceValues:
    @pytest.mark.parametrize("confidence_score", [-0.1, 1.1, -5.0, 100.0])
    def test_raises_when_confidence_is_out_of_range(self, confidence_score: float) -> None:
        result = make_result(confidence_score=confidence_score)

        with pytest.raises(InvalidPatientEducationConfidenceValueError):
            _validator().validate(result, make_input())

    def test_accepts_a_none_confidence_value(self) -> None:
        result = make_result(confidence_score=None)
        _validator().validate(result, make_input())

    @pytest.mark.parametrize("confidence_score", [0.0, 1.0, 0.5])
    def test_accepts_boundary_valid_confidence_scores(self, confidence_score: float) -> None:
        result = make_result(confidence_score=confidence_score)
        _validator().validate(result, make_input())


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
    def test_raises_when_patient_summary_contains_a_placeholder(self, placeholder: str) -> None:
        result = make_result(patient_summary=f"Summary: {placeholder}")

        with pytest.raises(HallucinatedRecommendationError) as exc_info:
            _validator().validate(result, make_input())
        assert exc_info.value.field_name == "patient_summary"

    def test_raises_when_diagnosis_explanation_contains_a_placeholder(self) -> None:
        result = make_result(diagnosis_explanation="Explanation: TBD")

        with pytest.raises(HallucinatedRecommendationError):
            _validator().validate(result, make_input())

    def test_raises_when_lifestyle_advice_contains_a_placeholder(self) -> None:
        result = make_result(lifestyle_advice=("[insert advice]",))

        with pytest.raises(HallucinatedRecommendationError) as exc_info:
            _validator().validate(result, make_input())
        assert exc_info.value.field_name == "lifestyle_advice"

    def test_raises_when_diet_advice_contains_a_placeholder(self) -> None:
        result = make_result(diet_advice=("TBD",))

        with pytest.raises(HallucinatedRecommendationError) as exc_info:
            _validator().validate(result, make_input())
        assert exc_info.value.field_name == "diet_advice"

    def test_raises_when_exercise_advice_contains_a_placeholder(self) -> None:
        result = make_result(exercise_advice=("TBD",))

        with pytest.raises(HallucinatedRecommendationError) as exc_info:
            _validator().validate(result, make_input())
        assert exc_info.value.field_name == "exercise_advice"

    def test_raises_when_follow_up_plan_contains_a_placeholder(self) -> None:
        result = make_result(follow_up_plan=("TBD",))

        with pytest.raises(HallucinatedRecommendationError) as exc_info:
            _validator().validate(result, make_input())
        assert exc_info.value.field_name == "follow_up_plan"

    def test_raises_when_patient_checklist_contains_a_placeholder(self) -> None:
        result = make_result(patient_checklist=("TBD",))

        with pytest.raises(HallucinatedRecommendationError) as exc_info:
            _validator().validate(result, make_input())
        assert exc_info.value.field_name == "patient_checklist"

    def test_does_not_flag_ordinary_clinical_language(self) -> None:
        _validator().validate(make_result(), make_input())


class TestValidateCheckOrdering:
    def test_unsafe_instruction_is_checked_before_confidence_value(self) -> None:
        result = make_result(
            medication_instructions=("double your dose",),
            confidence_score=5.0,
        )

        with pytest.raises(UnsafeInstructionError):
            _validator().validate(result, make_input())

    def test_confidence_value_is_checked_before_hallucinated_placeholders(self) -> None:
        result = make_result(
            patient_summary="Summary: TBD",
            confidence_score=5.0,
        )

        with pytest.raises(InvalidPatientEducationConfidenceValueError):
            _validator().validate(result, make_input())
