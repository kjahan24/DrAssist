"""Unit tests for the `DoctorSchedule` aggregate's invariants, including
`overlaps_with` — the pure time-range check `AddDoctorSchedule` relies on."""

from datetime import time
from uuid import uuid4

import pytest

from app.modules.doctor.domain.entities import DoctorSchedule
from app.modules.doctor.domain.enums import DayOfWeek
from app.modules.doctor.domain.events import DoctorScheduleAdded
from app.modules.doctor.domain.exceptions import (
    InvalidBreakTimeError,
    InvalidScheduleTimeRangeError,
)


def _make_schedule(**overrides: object) -> DoctorSchedule:
    defaults: dict[str, object] = {
        "doctor_id": uuid4(),
        "day_of_week": DayOfWeek.MONDAY,
        "start_time": time(9, 0),
        "end_time": time(17, 0),
    }
    defaults.update(overrides)
    return DoctorSchedule.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_records_schedule_added_event(self) -> None:
        doctor_id = uuid4()
        schedule = _make_schedule(doctor_id=doctor_id)

        assert schedule.doctor_id == doctor_id
        assert schedule.is_available is True
        events = schedule.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DoctorScheduleAdded)
        assert events[0].day_of_week == "monday"

    def test_start_time_after_end_time_is_rejected(self) -> None:
        with pytest.raises(InvalidScheduleTimeRangeError):
            _make_schedule(start_time=time(17, 0), end_time=time(9, 0))

    def test_start_time_equal_to_end_time_is_rejected(self) -> None:
        with pytest.raises(InvalidScheduleTimeRangeError):
            _make_schedule(start_time=time(9, 0), end_time=time(9, 0))

    def test_break_start_without_break_end_is_rejected(self) -> None:
        with pytest.raises(InvalidBreakTimeError):
            _make_schedule(break_start=time(12, 0), break_end=None)

    def test_break_end_without_break_start_is_rejected(self) -> None:
        with pytest.raises(InvalidBreakTimeError):
            _make_schedule(break_start=None, break_end=time(13, 0))

    def test_break_outside_shift_bounds_is_rejected(self) -> None:
        with pytest.raises(InvalidBreakTimeError):
            _make_schedule(break_start=time(8, 0), break_end=time(8, 30))

    def test_break_start_after_break_end_is_rejected(self) -> None:
        with pytest.raises(InvalidBreakTimeError):
            _make_schedule(break_start=time(13, 0), break_end=time(12, 0))

    def test_valid_break_within_shift_is_accepted(self) -> None:
        schedule = _make_schedule(break_start=time(12, 0), break_end=time(13, 0))
        assert schedule.break_start == time(12, 0)
        assert schedule.break_end == time(13, 0)


class TestOverlapsWith:
    def test_overlapping_ranges_overlap(self) -> None:
        first = _make_schedule(start_time=time(9, 0), end_time=time(13, 0))
        second = _make_schedule(start_time=time(12, 0), end_time=time(17, 0))
        assert first.overlaps_with(second) is True
        assert second.overlaps_with(first) is True

    def test_adjacent_ranges_do_not_overlap(self) -> None:
        first = _make_schedule(start_time=time(9, 0), end_time=time(12, 0))
        second = _make_schedule(start_time=time(12, 0), end_time=time(17, 0))
        assert first.overlaps_with(second) is False
        assert second.overlaps_with(first) is False

    def test_disjoint_ranges_do_not_overlap(self) -> None:
        first = _make_schedule(start_time=time(9, 0), end_time=time(11, 0))
        second = _make_schedule(start_time=time(14, 0), end_time=time(17, 0))
        assert first.overlaps_with(second) is False

    def test_identical_ranges_overlap(self) -> None:
        first = _make_schedule(start_time=time(9, 0), end_time=time(17, 0))
        second = _make_schedule(start_time=time(9, 0), end_time=time(17, 0))
        assert first.overlaps_with(second) is True
