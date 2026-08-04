"""Unit tests for `DefaultLabInterpretationValidator`."""

import pytest

from app.modules.lab_interpretation_ai.domain.enums import LabFindingFlag
from app.modules.lab_interpretation_ai.domain.exceptions import (
    HallucinatedLabValueError,
    MissingLabReasoningError,
)
from app.modules.lab_interpretation_ai.infrastructure.validation.lab_interpretation_validator import (  # noqa: E501
    DefaultLabInterpretationValidator,
)
from tests.unit.modules.lab_interpretation_ai.application.fakes import make_finding, make_result


def _validator() -> DefaultLabInterpretationValidator:
    return DefaultLabInterpretationValidator()


class TestValidateHappyPath:
    def test_accepts_a_well_formed_result(self) -> None:
        _validator().validate(make_result())


class TestValidateMissingReasoning:
    def test_raises_when_overall_interpretation_is_blank(self) -> None:
        result = make_result(overall_interpretation="")

        with pytest.raises(MissingLabReasoningError):
            _validator().validate(result)

    def test_raises_when_clinical_significance_is_blank_but_findings_were_reported(self) -> None:
        result = make_result(clinical_significance="")

        with pytest.raises(MissingLabReasoningError):
            _validator().validate(result)

    def test_accepts_blank_clinical_significance_when_nothing_else_was_reported(self) -> None:
        result = make_result(
            findings=(),
            clinical_significance="",
            supporting_evidence=(),
            potential_causes=(),
            suggested_follow_up_tests=(),
            monitoring_recommendations=(),
            red_flag_warnings=(),
        )

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
    def test_raises_when_overall_interpretation_contains_a_placeholder(
        self, placeholder: str
    ) -> None:
        result = make_result(overall_interpretation=f"Interpretation: {placeholder}")

        with pytest.raises(HallucinatedLabValueError) as exc_info:
            _validator().validate(result)
        assert exc_info.value.field_name == "overall_interpretation"

    def test_raises_when_clinical_significance_contains_a_placeholder(self) -> None:
        result = make_result(clinical_significance="Significance: TBD")

        with pytest.raises(HallucinatedLabValueError):
            _validator().validate(result)

    def test_raises_when_a_finding_test_name_contains_a_placeholder(self) -> None:
        result = make_result(findings=(make_finding(test_name="[insert test]"),))

        with pytest.raises(HallucinatedLabValueError) as exc_info:
            _validator().validate(result)
        assert exc_info.value.field_name == "findings"

    def test_raises_when_supporting_evidence_contains_a_placeholder(self) -> None:
        result = make_result(supporting_evidence=("TBD",))

        with pytest.raises(HallucinatedLabValueError) as exc_info:
            _validator().validate(result)
        assert exc_info.value.field_name == "supporting_evidence"

    def test_raises_when_a_red_flag_warning_contains_a_placeholder(self) -> None:
        result = make_result(red_flag_warnings=("[insert warning]",))

        with pytest.raises(HallucinatedLabValueError) as exc_info:
            _validator().validate(result)
        assert exc_info.value.field_name == "red_flag_warnings"

    def test_does_not_flag_ordinary_clinical_language(self) -> None:
        _validator().validate(make_result())


class TestValidateCheckOrdering:
    def test_missing_reasoning_is_checked_before_hallucinated_placeholders(self) -> None:
        result = make_result(overall_interpretation="", clinical_significance="TBD")

        with pytest.raises(MissingLabReasoningError):
            _validator().validate(result)

    def test_normal_flag_findings_do_not_affect_validation(self) -> None:
        result = make_result(findings=(make_finding(flag=LabFindingFlag.NORMAL),))
        _validator().validate(result)
