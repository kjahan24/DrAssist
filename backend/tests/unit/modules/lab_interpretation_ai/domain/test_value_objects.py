"""Unit tests for the AI Lab Interpretation module's domain value objects."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.lab_interpretation_ai.domain.enums import (
    LabFindingFlag,
    LabInterpretationOutputFormat,
    LabInterpretationSetting,
)
from app.modules.lab_interpretation_ai.domain.exceptions import (
    DuplicateLabValueError,
    ImpossibleLabValueRangeError,
    InvalidLabInterpretationInputError,
    InvalidLabUnitError,
    MalformedLabValueError,
)
from app.modules.lab_interpretation_ai.domain.value_objects import (
    LabFinding,
    LabInterpretationInput,
    LabInterpretationResult,
    LabValue,
)


def _lab_value(**overrides: object) -> LabValue:
    defaults: dict[str, object] = {
        "test_name": "Potassium",
        "value": "4.2",
        "numeric_value": 4.2,
        "unit": "mmol/L",
    }
    defaults.update(overrides)
    return LabValue(**defaults)  # type: ignore[arg-type]


def _input(**overrides: object) -> LabInterpretationInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "lab_values": (_lab_value(),),
        "lab_setting": LabInterpretationSetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return LabInterpretationInput(**defaults)  # type: ignore[arg-type]


class TestLabValue:
    def test_accepts_a_well_formed_value(self) -> None:
        lab_value = _lab_value()
        assert lab_value.test_name == "Potassium"
        assert lab_value.numeric_value == 4.2

    def test_accepts_a_qualitative_value_with_no_numeric_value(self) -> None:
        lab_value = _lab_value(value="Trace", numeric_value=None, unit=None)
        assert lab_value.numeric_value is None

    def test_raises_when_test_name_is_blank(self) -> None:
        with pytest.raises(MalformedLabValueError):
            _lab_value(test_name="   ")

    def test_raises_when_value_is_blank(self) -> None:
        with pytest.raises(MalformedLabValueError):
            _lab_value(value="")

    def test_raises_when_numeric_value_is_negative(self) -> None:
        with pytest.raises(ImpossibleLabValueRangeError) as exc_info:
            _lab_value(numeric_value=-1.0)
        assert exc_info.value.test_name == "Potassium"

    def test_raises_when_numeric_value_is_not_finite(self) -> None:
        with pytest.raises(ImpossibleLabValueRangeError):
            _lab_value(numeric_value=float("inf"))

    def test_accepts_a_zero_numeric_value(self) -> None:
        _lab_value(numeric_value=0.0)

    def test_raises_when_unit_is_blank(self) -> None:
        with pytest.raises(InvalidLabUnitError):
            _lab_value(unit="   ")

    def test_accepts_a_missing_unit(self) -> None:
        _lab_value(unit=None)


class TestLabInterpretationInput:
    def test_accepts_a_well_formed_input(self) -> None:
        _input()

    def test_raises_when_lab_values_is_empty(self) -> None:
        with pytest.raises(InvalidLabInterpretationInputError):
            _input(lab_values=())

    def test_raises_when_language_is_blank(self) -> None:
        with pytest.raises(InvalidLabInterpretationInputError):
            _input(language="   ")

    @pytest.mark.parametrize("patient_age", [-1, 151])
    def test_raises_when_patient_age_is_out_of_range(self, patient_age: int) -> None:
        with pytest.raises(InvalidLabInterpretationInputError):
            _input(patient_age=patient_age)

    @pytest.mark.parametrize("patient_age", [0, 150, 42])
    def test_accepts_boundary_patient_ages(self, patient_age: int) -> None:
        _input(patient_age=patient_age)

    def test_accepts_a_missing_patient_age(self) -> None:
        _input(patient_age=None)

    def test_raises_on_an_exact_duplicate_lab_value(self) -> None:
        with pytest.raises(DuplicateLabValueError) as exc_info:
            _input(lab_values=(_lab_value(), _lab_value()))
        assert exc_info.value.test_name == "Potassium"

    def test_allows_two_readings_of_the_same_test_with_different_values(self) -> None:
        _input(
            lab_values=(
                _lab_value(value="4.2", numeric_value=4.2),
                _lab_value(value="4.5", numeric_value=4.5),
            )
        )

    def test_allows_two_identical_readings_taken_at_different_times(self) -> None:
        _input(
            lab_values=(
                _lab_value(collected_at=datetime(2026, 1, 1, tzinfo=UTC)),
                _lab_value(collected_at=datetime(2026, 2, 1, tzinfo=UTC)),
            )
        )


class TestLabFinding:
    def test_carries_its_fields(self) -> None:
        finding = LabFinding(
            test_name="Potassium",
            value="6.8",
            numeric_value=6.8,
            unit="mmol/L",
            flag=LabFindingFlag.CRITICAL_HIGH,
        )
        assert finding.flag is LabFindingFlag.CRITICAL_HIGH


class TestLabInterpretationResult:
    def _result(self, **overrides: object) -> LabInterpretationResult:
        defaults: dict[str, object] = {
            "overall_interpretation": "Findings reviewed.",
            "findings": (
                LabFinding(
                    test_name="Potassium",
                    value="4.2",
                    numeric_value=4.2,
                    unit="mmol/L",
                    flag=LabFindingFlag.NORMAL,
                ),
                LabFinding(
                    test_name="Sodium",
                    value="128",
                    numeric_value=128.0,
                    unit="mmol/L",
                    flag=LabFindingFlag.ABNORMAL_LOW,
                ),
                LabFinding(
                    test_name="Glucose",
                    value="410",
                    numeric_value=410.0,
                    unit="mg/dL",
                    flag=LabFindingFlag.CRITICAL_HIGH,
                ),
            ),
            "clinical_significance": "Hyponatremia and hyperglycemia noted.",
            "supporting_evidence": (),
            "potential_causes": (),
            "suggested_follow_up_tests": (),
            "monitoring_recommendations": (),
            "red_flag_warnings": (),
            "confidence_score": 0.7,
            "raw_text": "{}",
            "output_format": LabInterpretationOutputFormat.JSON,
        }
        defaults.update(overrides)
        return LabInterpretationResult(**defaults)  # type: ignore[arg-type]

    def test_abnormal_findings_excludes_normal_and_critical(self) -> None:
        result = self._result()
        assert [f.test_name for f in result.abnormal_findings] == ["Sodium"]

    def test_critical_values_excludes_normal_and_abnormal(self) -> None:
        result = self._result()
        assert [f.test_name for f in result.critical_values] == ["Glucose"]

    def test_is_empty_true_when_every_field_is_vacuous(self) -> None:
        result = self._result(
            overall_interpretation="",
            findings=(),
            clinical_significance="",
            supporting_evidence=(),
            potential_causes=(),
            suggested_follow_up_tests=(),
            monitoring_recommendations=(),
            red_flag_warnings=(),
        )
        assert result.is_empty is True

    def test_is_empty_false_when_overall_interpretation_is_present(self) -> None:
        result = self._result(
            findings=(),
            clinical_significance="",
            supporting_evidence=(),
            potential_causes=(),
            suggested_follow_up_tests=(),
            monitoring_recommendations=(),
            red_flag_warnings=(),
        )
        assert result.is_empty is False
