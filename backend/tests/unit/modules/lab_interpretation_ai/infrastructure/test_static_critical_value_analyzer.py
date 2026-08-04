"""Unit tests for `StaticCriticalValueAnalyzer`."""

from app.modules.lab_interpretation_ai.domain.enums import LabFindingFlag
from app.modules.lab_interpretation_ai.infrastructure.critical_values.static_critical_value_analyzer import (  # noqa: E501
    StaticCriticalValueAnalyzer,
)


class TestClassify:
    def test_returns_none_when_numeric_value_is_missing(self) -> None:
        analyzer = StaticCriticalValueAnalyzer()
        assert analyzer.classify(test_name="Potassium", numeric_value=None) is None

    def test_returns_none_for_an_unrecognized_test(self) -> None:
        analyzer = StaticCriticalValueAnalyzer()
        assert analyzer.classify(test_name="Some Rare Test", numeric_value=5.0) is None

    def test_is_case_and_whitespace_insensitive_on_test_name(self) -> None:
        analyzer = StaticCriticalValueAnalyzer()
        assert analyzer.classify(test_name="  Potassium  ", numeric_value=4.2) is (
            LabFindingFlag.NORMAL
        )

    def test_classifies_a_normal_value(self) -> None:
        analyzer = StaticCriticalValueAnalyzer()
        assert analyzer.classify(test_name="potassium", numeric_value=4.2) == (
            LabFindingFlag.NORMAL
        )

    def test_classifies_an_abnormal_low_value(self) -> None:
        analyzer = StaticCriticalValueAnalyzer()
        assert analyzer.classify(test_name="potassium", numeric_value=3.0) == (
            LabFindingFlag.ABNORMAL_LOW
        )

    def test_classifies_a_critical_low_value(self) -> None:
        analyzer = StaticCriticalValueAnalyzer()
        assert analyzer.classify(test_name="potassium", numeric_value=2.0) == (
            LabFindingFlag.CRITICAL_LOW
        )

    def test_classifies_an_abnormal_high_value(self) -> None:
        analyzer = StaticCriticalValueAnalyzer()
        assert analyzer.classify(test_name="potassium", numeric_value=5.5) == (
            LabFindingFlag.ABNORMAL_HIGH
        )

    def test_classifies_a_critical_high_value(self) -> None:
        analyzer = StaticCriticalValueAnalyzer()
        assert analyzer.classify(test_name="potassium", numeric_value=7.0) == (
            LabFindingFlag.CRITICAL_HIGH
        )

    def test_never_reports_critical_low_when_no_critical_low_threshold_exists(self) -> None:
        analyzer = StaticCriticalValueAnalyzer()
        assert analyzer.classify(test_name="ldl cholesterol", numeric_value=0.0) != (
            LabFindingFlag.CRITICAL_LOW
        )

    def test_accepts_a_custom_reference_range_table(self) -> None:
        from app.modules.lab_interpretation_ai.infrastructure.critical_values.static_critical_value_analyzer import (  # noqa: E501
            _ReferenceRange,
        )

        analyzer = StaticCriticalValueAnalyzer(
            {"custom test": _ReferenceRange(normal_low=1.0, normal_high=2.0)}
        )

        assert analyzer.classify(test_name="custom test", numeric_value=5.0) == (
            LabFindingFlag.ABNORMAL_HIGH
        )
