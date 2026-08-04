"""`LabTrendAnalysisService` — this task's own explicitly-named
APPLICATION service. Needs no port: given a caller-supplied collection of
`LabValue`s, comparing readings of the same test over time is pure
arithmetic/ordering, not knowledge-dependent, the same "pure, no port
needed" reasoning `app.modules.medical_reasoning_ai.application.services
.evidence_analysis_service.EvidenceAnalysisService.find_duplicates`
documents for its own module.

This task's own INPUT section does not name a separate "prior/historical
lab values" field — trend analysis therefore operates over whatever
`LabInterpretationInput.lab_values` the caller included in *this* request:
when it contains two or more readings of the same test (distinguished by
`LabValue.collected_at` and/or a different `numeric_value` — see
`LabValue.__post_init__`'s own docstring for why *identical* repeated
readings are instead rejected as `DuplicateLabValueError`), a trend
description is produced; a single snapshot per test degrades gracefully
to "no trend data available" (an empty result, not an error) rather than
requiring a field this task never asked for.
"""

from app.modules.lab_interpretation_ai.domain.value_objects import LabValue

_MIN_READINGS_FOR_A_TREND = 2


class LabTrendAnalysisService:
    def group_by_test(self, values: tuple[LabValue, ...]) -> dict[str, tuple[LabValue, ...]]:
        groups: dict[str, list[LabValue]] = {}
        for value in values:
            key = value.test_name.strip().lower()
            groups.setdefault(key, []).append(value)
        return {key: tuple(group) for key, group in groups.items()}

    def analyze_trend(self, values: tuple[LabValue, ...]) -> str | None:
        numeric_readings = [value for value in values if value.numeric_value is not None]
        if len(numeric_readings) < _MIN_READINGS_FOR_A_TREND:
            return None

        ordered = sorted(numeric_readings, key=self._sort_key)
        first, last = ordered[0], ordered[-1]
        assert first.numeric_value is not None
        assert last.numeric_value is not None

        if last.numeric_value == first.numeric_value:
            direction = "stable"
        elif last.numeric_value > first.numeric_value:
            direction = "rising"
        else:
            direction = "falling"

        unit_suffix = f" {last.unit}" if last.unit else ""
        return (
            f"{last.test_name}: {direction} from {first.numeric_value}{unit_suffix} to "
            f"{last.numeric_value}{unit_suffix} across {len(ordered)} readings"
        )

    def analyze_all_trends(self, values: tuple[LabValue, ...]) -> tuple[str, ...]:
        trends = [
            trend
            for group in self.group_by_test(values).values()
            if (trend := self.analyze_trend(group)) is not None
        ]
        return tuple(trends)

    def _sort_key(self, value: LabValue) -> tuple[int, str]:
        if value.collected_at is None:
            return (0, "")
        return (1, value.collected_at.isoformat())
