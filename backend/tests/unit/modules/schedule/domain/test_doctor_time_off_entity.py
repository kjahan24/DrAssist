"""Unit tests for the `DoctorTimeOff` aggregate's own invariants:
"end_datetime must be later than start_datetime", `overlaps_with()`, and
`update_details()`."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.schedule.domain.entities import DoctorTimeOff
from app.modules.schedule.domain.events import DoctorTimeOffCreated, DoctorTimeOffUpdated
from app.modules.schedule.domain.exceptions import InvalidTimeOffRangeError


def _make_time_off(**overrides: object) -> DoctorTimeOff:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "doctor_id": uuid4(),
        "start_datetime": datetime(2026, 6, 1, 9, 0, tzinfo=UTC),
        "end_datetime": datetime(2026, 6, 5, 17, 0, tzinfo=UTC),
    }
    defaults.update(overrides)
    return DoctorTimeOff.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_sets_identity_fields_and_records_event(self) -> None:
        organization_id = uuid4()
        doctor_id = uuid4()

        time_off = _make_time_off(organization_id=organization_id, doctor_id=doctor_id)

        assert time_off.organization_id == organization_id
        assert time_off.doctor_id == doctor_id
        events = time_off.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DoctorTimeOffCreated)
        assert events[0].time_off_id == time_off.id
        assert events[0].doctor_id == doctor_id

    def test_reason_defaults_to_none(self) -> None:
        assert _make_time_off().reason is None

    def test_reason_is_accepted(self) -> None:
        time_off = _make_time_off(reason="Annual leave")
        assert time_off.reason == "Annual leave"

    def test_end_before_start_is_rejected(self) -> None:
        with pytest.raises(InvalidTimeOffRangeError):
            _make_time_off(
                start_datetime=datetime(2026, 6, 5, tzinfo=UTC),
                end_datetime=datetime(2026, 6, 1, tzinfo=UTC),
            )

    def test_end_equal_to_start_is_rejected(self) -> None:
        same = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)
        with pytest.raises(InvalidTimeOffRangeError):
            _make_time_off(start_datetime=same, end_datetime=same)


class TestOverlapsWith:
    def test_overlapping_ranges_return_true(self) -> None:
        first = _make_time_off(
            start_datetime=datetime(2026, 6, 1, tzinfo=UTC),
            end_datetime=datetime(2026, 6, 10, tzinfo=UTC),
        )
        second = _make_time_off(
            start_datetime=datetime(2026, 6, 5, tzinfo=UTC),
            end_datetime=datetime(2026, 6, 15, tzinfo=UTC),
        )
        assert first.overlaps_with(second) is True
        assert second.overlaps_with(first) is True

    def test_adjacent_ranges_do_not_overlap(self) -> None:
        first = _make_time_off(
            start_datetime=datetime(2026, 6, 1, tzinfo=UTC),
            end_datetime=datetime(2026, 6, 5, tzinfo=UTC),
        )
        second = _make_time_off(
            start_datetime=datetime(2026, 6, 5, tzinfo=UTC),
            end_datetime=datetime(2026, 6, 10, tzinfo=UTC),
        )
        assert first.overlaps_with(second) is False

    def test_disjoint_ranges_do_not_overlap(self) -> None:
        first = _make_time_off(
            start_datetime=datetime(2026, 6, 1, tzinfo=UTC),
            end_datetime=datetime(2026, 6, 2, tzinfo=UTC),
        )
        second = _make_time_off(
            start_datetime=datetime(2026, 7, 1, tzinfo=UTC),
            end_datetime=datetime(2026, 7, 2, tzinfo=UTC),
        )
        assert first.overlaps_with(second) is False


class TestUpdateDetails:
    def test_update_changes_fields_and_records_event(self) -> None:
        time_off = _make_time_off()
        time_off.pull_events()

        new_start = datetime(2026, 7, 1, tzinfo=UTC)
        new_end = datetime(2026, 7, 5, tzinfo=UTC)
        time_off.update_details(start_datetime=new_start, end_datetime=new_end, reason="Updated")

        assert time_off.start_datetime == new_start
        assert time_off.end_datetime == new_end
        assert time_off.reason == "Updated"
        events = time_off.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], DoctorTimeOffUpdated)

    def test_update_leaves_unspecified_fields_unchanged(self) -> None:
        original_end = datetime(2026, 6, 5, 17, 0, tzinfo=UTC)
        time_off = _make_time_off(end_datetime=original_end)
        time_off.update_details(reason="Just a reason change")
        assert time_off.end_datetime == original_end

    def test_updating_end_alone_is_validated_against_existing_start(self) -> None:
        time_off = _make_time_off(
            start_datetime=datetime(2026, 6, 1, tzinfo=UTC),
            end_datetime=datetime(2026, 6, 10, tzinfo=UTC),
        )
        with pytest.raises(InvalidTimeOffRangeError):
            time_off.update_details(end_datetime=datetime(2026, 5, 1, tzinfo=UTC))
