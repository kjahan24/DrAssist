"""Unit tests for the `DoctorSchedule` aggregate's own invariants:
"end_time must be later than start_time", "slot_duration_minutes must be
greater than zero", `overlaps_with()`, `update_details()`, and
`activate()`/`deactivate()`."""

from datetime import time
from uuid import uuid4

import pytest

from app.modules.schedule.domain.entities import DoctorSchedule
from app.modules.schedule.domain.enums import Weekday
from app.modules.schedule.domain.events import (
    DoctorScheduleActiveChanged,
    DoctorScheduleCreated,
    DoctorScheduleUpdated,
)
from app.modules.schedule.domain.exceptions import (
    InvalidScheduleTimeRangeError,
    InvalidSlotDurationError,
)


def _make_schedule(**overrides: object) -> DoctorSchedule:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "doctor_id": uuid4(),
        "weekday": Weekday.MONDAY,
        "start_time": time(9, 0),
        "end_time": time(12, 0),
        "slot_duration_minutes": 30,
    }
    defaults.update(overrides)
    return DoctorSchedule.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_sets_identity_fields_and_records_event(self) -> None:
        organization_id = uuid4()
        doctor_id = uuid4()

        schedule = _make_schedule(organization_id=organization_id, doctor_id=doctor_id)

        assert schedule.organization_id == organization_id
        assert schedule.doctor_id == doctor_id
        events = schedule.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DoctorScheduleCreated)
        assert events[0].schedule_id == schedule.id
        assert events[0].doctor_id == doctor_id

    def test_is_active_defaults_to_true(self) -> None:
        assert _make_schedule().is_active is True

    def test_is_active_can_be_set_false_at_creation(self) -> None:
        assert _make_schedule(is_active=False).is_active is False

    def test_end_time_before_start_time_is_rejected(self) -> None:
        with pytest.raises(InvalidScheduleTimeRangeError):
            _make_schedule(start_time=time(12, 0), end_time=time(9, 0))

    def test_end_time_equal_to_start_time_is_rejected(self) -> None:
        with pytest.raises(InvalidScheduleTimeRangeError):
            _make_schedule(start_time=time(9, 0), end_time=time(9, 0))

    def test_zero_slot_duration_is_rejected(self) -> None:
        with pytest.raises(InvalidSlotDurationError):
            _make_schedule(slot_duration_minutes=0)

    def test_negative_slot_duration_is_rejected(self) -> None:
        with pytest.raises(InvalidSlotDurationError):
            _make_schedule(slot_duration_minutes=-15)


class TestOverlapsWith:
    def test_overlapping_ranges_return_true(self) -> None:
        first = _make_schedule(start_time=time(9, 0), end_time=time(11, 0))
        second = _make_schedule(start_time=time(10, 0), end_time=time(12, 0))
        assert first.overlaps_with(second) is True
        assert second.overlaps_with(first) is True

    def test_adjacent_ranges_do_not_overlap(self) -> None:
        first = _make_schedule(start_time=time(9, 0), end_time=time(11, 0))
        second = _make_schedule(start_time=time(11, 0), end_time=time(13, 0))
        assert first.overlaps_with(second) is False
        assert second.overlaps_with(first) is False

    def test_disjoint_ranges_do_not_overlap(self) -> None:
        first = _make_schedule(start_time=time(9, 0), end_time=time(10, 0))
        second = _make_schedule(start_time=time(14, 0), end_time=time(15, 0))
        assert first.overlaps_with(second) is False

    def test_fully_contained_range_overlaps(self) -> None:
        outer = _make_schedule(start_time=time(9, 0), end_time=time(17, 0))
        inner = _make_schedule(start_time=time(12, 0), end_time=time(13, 0))
        assert outer.overlaps_with(inner) is True


class TestUpdateDetails:
    def test_update_changes_fields_and_records_event(self) -> None:
        schedule = _make_schedule()
        schedule.pull_events()

        schedule.update_details(start_time=time(8, 0), end_time=time(16, 0))

        assert schedule.start_time == time(8, 0)
        assert schedule.end_time == time(16, 0)
        events = schedule.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DoctorScheduleUpdated)

    def test_update_leaves_unspecified_fields_unchanged(self) -> None:
        schedule = _make_schedule(slot_duration_minutes=20)
        schedule.update_details(start_time=time(8, 0))
        assert schedule.slot_duration_minutes == 20
        assert schedule.end_time == time(12, 0)

    def test_updating_end_time_alone_is_validated_against_existing_start(self) -> None:
        schedule = _make_schedule(start_time=time(9, 0), end_time=time(12, 0))
        with pytest.raises(InvalidScheduleTimeRangeError):
            schedule.update_details(end_time=time(8, 0))

    def test_updating_slot_duration_to_zero_is_rejected(self) -> None:
        schedule = _make_schedule()
        with pytest.raises(InvalidSlotDurationError):
            schedule.update_details(slot_duration_minutes=0)


class TestActivateDeactivate:
    def test_deactivate_sets_is_active_false_and_records_event(self) -> None:
        schedule = _make_schedule()
        schedule.pull_events()

        schedule.deactivate()

        assert schedule.is_active is False
        events = schedule.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DoctorScheduleActiveChanged)
        assert events[0].is_active is False

    def test_deactivate_when_already_inactive_records_no_event(self) -> None:
        schedule = _make_schedule(is_active=False)
        schedule.pull_events()
        schedule.deactivate()
        assert schedule.pull_events() == []

    def test_activate_sets_is_active_true_and_records_event(self) -> None:
        schedule = _make_schedule(is_active=False)
        schedule.pull_events()

        schedule.activate()

        assert schedule.is_active is True
        events = schedule.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DoctorScheduleActiveChanged)
        assert events[0].is_active is True

    def test_activate_when_already_active_records_no_event(self) -> None:
        schedule = _make_schedule(is_active=True)
        schedule.pull_events()
        schedule.activate()
        assert schedule.pull_events() == []
