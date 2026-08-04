"""Unit tests for `LabTrendAnalysisService`."""

from datetime import UTC, datetime

from app.modules.lab_interpretation_ai.application.services.lab_trend_analysis_service import (
    LabTrendAnalysisService,
)
from tests.unit.modules.lab_interpretation_ai.application.fakes import make_lab_value


class TestGroupByTest:
    def test_groups_case_and_whitespace_insensitively(self) -> None:
        service = LabTrendAnalysisService()
        values = (
            make_lab_value(test_name="Potassium"),
            make_lab_value(test_name=" potassium "),
            make_lab_value(test_name="Sodium", numeric_value=140.0),
        )

        groups = service.group_by_test(values)

        assert len(groups["potassium"]) == 2
        assert len(groups["sodium"]) == 1


class TestAnalyzeTrend:
    def test_returns_none_with_fewer_than_two_numeric_readings(self) -> None:
        service = LabTrendAnalysisService()
        assert service.analyze_trend((make_lab_value(),)) is None

    def test_returns_none_when_readings_are_all_qualitative(self) -> None:
        service = LabTrendAnalysisService()
        values = (
            make_lab_value(value="Trace", numeric_value=None, unit=None),
            make_lab_value(value="Positive", numeric_value=None, unit=None),
        )
        assert service.analyze_trend(values) is None

    def test_reports_rising_when_the_later_reading_is_higher(self) -> None:
        service = LabTrendAnalysisService()
        values = (
            make_lab_value(numeric_value=4.0, collected_at=datetime(2026, 1, 1, tzinfo=UTC)),
            make_lab_value(numeric_value=5.5, collected_at=datetime(2026, 2, 1, tzinfo=UTC)),
        )

        trend = service.analyze_trend(values)

        assert trend is not None
        assert "rising" in trend
        assert "4.0" in trend
        assert "5.5" in trend

    def test_reports_falling_when_the_later_reading_is_lower(self) -> None:
        service = LabTrendAnalysisService()
        values = (
            make_lab_value(numeric_value=6.0, collected_at=datetime(2026, 1, 1, tzinfo=UTC)),
            make_lab_value(numeric_value=4.0, collected_at=datetime(2026, 2, 1, tzinfo=UTC)),
        )

        trend = service.analyze_trend(values)

        assert trend is not None
        assert "falling" in trend

    def test_reports_stable_when_readings_are_equal(self) -> None:
        service = LabTrendAnalysisService()
        values = (
            make_lab_value(numeric_value=4.0, collected_at=datetime(2026, 1, 1, tzinfo=UTC)),
            make_lab_value(numeric_value=4.0, collected_at=datetime(2026, 2, 1, tzinfo=UTC)),
        )

        trend = service.analyze_trend(values)

        assert trend is not None
        assert "stable" in trend

    def test_orders_undated_readings_before_dated_ones(self) -> None:
        service = LabTrendAnalysisService()
        values = (
            make_lab_value(numeric_value=8.0, collected_at=datetime(2026, 1, 1, tzinfo=UTC)),
            make_lab_value(numeric_value=2.0, collected_at=None),
        )

        trend = service.analyze_trend(values)

        assert trend is not None
        assert "rising" in trend


class TestAnalyzeAllTrends:
    def test_produces_one_trend_per_test_with_enough_readings(self) -> None:
        service = LabTrendAnalysisService()
        values = (
            make_lab_value(
                test_name="Potassium",
                numeric_value=4.0,
                collected_at=datetime(2026, 1, 1, tzinfo=UTC),
            ),
            make_lab_value(
                test_name="Potassium",
                numeric_value=4.8,
                collected_at=datetime(2026, 2, 1, tzinfo=UTC),
            ),
            make_lab_value(test_name="Sodium", numeric_value=140.0),
        )

        trends = service.analyze_all_trends(values)

        assert len(trends) == 1
        assert "Potassium" in trends[0]

    def test_empty_when_no_test_has_two_readings(self) -> None:
        service = LabTrendAnalysisService()
        values = (make_lab_value(test_name="Potassium"), make_lab_value(test_name="Sodium"))

        assert service.analyze_all_trends(values) == ()
