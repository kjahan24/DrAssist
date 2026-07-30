"""Unit tests for the `Appointment` aggregate's own invariants: always
starting `Scheduled`, "end_time must be later than start_time", the
explicit status-transition map, and the "Completed/NoShow become
immutable" self-check `ensure_editable()` shares with `update_details()`
(while `Cancelled` remains editable)."""

from datetime import date, time
from uuid import uuid4

import pytest

from app.modules.appointment.domain.entities import Appointment
from app.modules.appointment.domain.enums import AppointmentStatus, AppointmentType
from app.modules.appointment.domain.events import (
    AppointmentCreated,
    AppointmentStatusChanged,
    AppointmentUpdated,
)
from app.modules.appointment.domain.exceptions import (
    AppointmentNotEditableError,
    AppointmentNumberRequiredError,
    InvalidAppointmentStatusTransitionError,
    InvalidAppointmentTimeRangeError,
)


def _make_appointment(**overrides: object) -> Appointment:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "doctor_id": uuid4(),
        "appointment_number": "APT-0001",
        "appointment_date": date(2026, 2, 1),
        "start_time": time(9, 0),
        "end_time": time(9, 30),
        "appointment_type": AppointmentType.CONSULTATION,
    }
    defaults.update(overrides)
    return Appointment.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_sets_identity_fields_and_records_event(self) -> None:
        organization_id = uuid4()
        patient_id = uuid4()
        doctor_id = uuid4()

        appointment = _make_appointment(
            organization_id=organization_id, patient_id=patient_id, doctor_id=doctor_id
        )

        assert appointment.organization_id == organization_id
        assert appointment.patient_id == patient_id
        assert appointment.doctor_id == doctor_id
        events = appointment.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], AppointmentCreated)
        assert events[0].appointment_id == appointment.id
        assert events[0].patient_id == patient_id
        assert events[0].doctor_id == doctor_id

    def test_always_starts_scheduled(self) -> None:
        assert _make_appointment().status is AppointmentStatus.SCHEDULED

    def test_blank_appointment_number_is_rejected(self) -> None:
        with pytest.raises(AppointmentNumberRequiredError):
            _make_appointment(appointment_number="   ")

    def test_appointment_number_is_stripped(self) -> None:
        appointment = _make_appointment(appointment_number="  APT-0002  ")
        assert appointment.appointment_number == "APT-0002"

    def test_end_time_before_start_time_is_rejected(self) -> None:
        with pytest.raises(InvalidAppointmentTimeRangeError):
            _make_appointment(start_time=time(10, 0), end_time=time(9, 0))

    def test_end_time_equal_to_start_time_is_rejected(self) -> None:
        with pytest.raises(InvalidAppointmentTimeRangeError):
            _make_appointment(start_time=time(9, 0), end_time=time(9, 0))

    def test_optional_fields_default_to_none(self) -> None:
        appointment = _make_appointment()
        assert appointment.reason_for_visit is None
        assert appointment.notes is None
        assert appointment.booked_by_user_id is None
        assert appointment.visit_id is None
        assert appointment.checked_in_at is None
        assert appointment.completed_at is None
        assert appointment.cancelled_at is None


class TestUpdateDetails:
    def test_update_changes_fields_and_records_event_while_scheduled(self) -> None:
        appointment = _make_appointment()
        appointment.pull_events()

        appointment.update_details(notes="Bring prior lab results", reason_for_visit="Follow-up")

        assert appointment.notes == "Bring prior lab results"
        assert appointment.reason_for_visit == "Follow-up"
        events = appointment.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], AppointmentUpdated)

    def test_update_leaves_unspecified_fields_unchanged(self) -> None:
        appointment = _make_appointment(notes="Original note")
        appointment.update_details(reason_for_visit="New reason")
        assert appointment.notes == "Original note"

    def test_rescheduling_revalidates_time_range(self) -> None:
        appointment = _make_appointment(start_time=time(9, 0), end_time=time(9, 30))
        with pytest.raises(InvalidAppointmentTimeRangeError):
            appointment.update_details(start_time=time(10, 0))

    def test_rescheduling_end_time_alone_is_validated_against_existing_start(self) -> None:
        appointment = _make_appointment(start_time=time(9, 0), end_time=time(9, 30))
        with pytest.raises(InvalidAppointmentTimeRangeError):
            appointment.update_details(end_time=time(8, 0))

    def test_rescheduling_both_times_together_is_allowed(self) -> None:
        appointment = _make_appointment(start_time=time(9, 0), end_time=time(9, 30))
        appointment.update_details(start_time=time(14, 0), end_time=time(14, 30))
        assert appointment.start_time == time(14, 0)
        assert appointment.end_time == time(14, 30)

    def test_update_while_cancelled_is_allowed(self) -> None:
        appointment = _make_appointment()
        appointment.cancel()
        appointment.update_details(notes="Cancelled by patient request")
        assert appointment.notes == "Cancelled by patient request"

    def test_update_once_completed_is_rejected(self) -> None:
        appointment = _make_appointment()
        appointment.check_in()
        appointment.complete()
        with pytest.raises(AppointmentNotEditableError):
            appointment.update_details(notes="Too late")

    def test_update_once_no_show_is_rejected(self) -> None:
        appointment = _make_appointment()
        appointment.mark_no_show()
        with pytest.raises(AppointmentNotEditableError):
            appointment.update_details(notes="Too late")


class TestConfirm:
    def test_confirm_from_scheduled_sets_status(self) -> None:
        appointment = _make_appointment()
        appointment.pull_events()

        appointment.confirm()

        assert appointment.status is AppointmentStatus.CONFIRMED
        events = appointment.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], AppointmentStatusChanged)
        assert events[0].status == "confirmed"

    def test_confirm_when_already_confirmed_is_rejected(self) -> None:
        appointment = _make_appointment()
        appointment.confirm()
        with pytest.raises(InvalidAppointmentStatusTransitionError):
            appointment.confirm()

    def test_confirm_once_checked_in_is_rejected(self) -> None:
        appointment = _make_appointment()
        appointment.check_in()
        with pytest.raises(InvalidAppointmentStatusTransitionError):
            appointment.confirm()


class TestCheckIn:
    def test_check_in_from_scheduled_sets_status_and_timestamp(self) -> None:
        appointment = _make_appointment()
        appointment.check_in()
        assert appointment.status is AppointmentStatus.CHECKED_IN
        assert appointment.checked_in_at is not None

    def test_check_in_from_confirmed_is_allowed(self) -> None:
        appointment = _make_appointment()
        appointment.confirm()
        appointment.check_in()
        assert appointment.status is AppointmentStatus.CHECKED_IN

    def test_check_in_twice_is_rejected(self) -> None:
        appointment = _make_appointment()
        appointment.check_in()
        with pytest.raises(InvalidAppointmentStatusTransitionError):
            appointment.check_in()


class TestStart:
    def test_start_from_checked_in_sets_status(self) -> None:
        appointment = _make_appointment()
        appointment.check_in()
        appointment.start()
        assert appointment.status is AppointmentStatus.IN_PROGRESS

    def test_start_from_scheduled_is_rejected(self) -> None:
        appointment = _make_appointment()
        with pytest.raises(InvalidAppointmentStatusTransitionError):
            appointment.start()


class TestComplete:
    def test_complete_from_checked_in_sets_status_and_timestamp(self) -> None:
        appointment = _make_appointment()
        appointment.check_in()
        appointment.complete()
        assert appointment.status is AppointmentStatus.COMPLETED
        assert appointment.completed_at is not None

    def test_complete_from_in_progress_is_allowed(self) -> None:
        appointment = _make_appointment()
        appointment.check_in()
        appointment.start()
        appointment.complete()
        assert appointment.status is AppointmentStatus.COMPLETED

    def test_complete_from_scheduled_is_rejected(self) -> None:
        appointment = _make_appointment()
        with pytest.raises(InvalidAppointmentStatusTransitionError):
            appointment.complete()

    def test_complete_without_visit_id_leaves_it_none(self) -> None:
        appointment = _make_appointment()
        appointment.check_in()
        appointment.complete()
        assert appointment.visit_id is None

    def test_complete_with_visit_id_records_it(self) -> None:
        visit_id = uuid4()
        appointment = _make_appointment()
        appointment.check_in()
        appointment.complete(visit_id=visit_id)
        assert appointment.visit_id == visit_id

    def test_cancelled_cannot_become_completed(self) -> None:
        appointment = _make_appointment()
        appointment.cancel()
        with pytest.raises(InvalidAppointmentStatusTransitionError):
            appointment.complete()


class TestCancel:
    def test_cancel_from_scheduled_sets_status_and_timestamp(self) -> None:
        appointment = _make_appointment()
        appointment.cancel()
        assert appointment.status is AppointmentStatus.CANCELLED
        assert appointment.cancelled_at is not None

    def test_cancel_from_in_progress_is_allowed(self) -> None:
        appointment = _make_appointment()
        appointment.check_in()
        appointment.start()
        appointment.cancel()
        assert appointment.status is AppointmentStatus.CANCELLED

    def test_cancel_an_already_cancelled_appointment_is_rejected(self) -> None:
        appointment = _make_appointment()
        appointment.cancel()
        with pytest.raises(InvalidAppointmentStatusTransitionError):
            appointment.cancel()

    def test_cancel_a_completed_appointment_is_rejected(self) -> None:
        appointment = _make_appointment()
        appointment.check_in()
        appointment.complete()
        with pytest.raises(InvalidAppointmentStatusTransitionError):
            appointment.cancel()


class TestMarkNoShow:
    def test_mark_no_show_from_scheduled_sets_status(self) -> None:
        appointment = _make_appointment()
        appointment.pull_events()

        appointment.mark_no_show()

        assert appointment.status is AppointmentStatus.NO_SHOW
        events = appointment.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], AppointmentStatusChanged)
        assert events[0].status == "no_show"

    def test_mark_no_show_from_confirmed_is_allowed(self) -> None:
        appointment = _make_appointment()
        appointment.confirm()
        appointment.mark_no_show()
        assert appointment.status is AppointmentStatus.NO_SHOW

    def test_mark_no_show_once_checked_in_is_rejected(self) -> None:
        appointment = _make_appointment()
        appointment.check_in()
        with pytest.raises(InvalidAppointmentStatusTransitionError):
            appointment.mark_no_show()


class TestEnsureEditable:
    def test_does_not_raise_while_scheduled(self) -> None:
        _make_appointment().ensure_editable()

    def test_does_not_raise_while_cancelled(self) -> None:
        appointment = _make_appointment()
        appointment.cancel()
        appointment.ensure_editable()

    def test_raises_once_completed(self) -> None:
        appointment = _make_appointment()
        appointment.check_in()
        appointment.complete()
        with pytest.raises(AppointmentNotEditableError):
            appointment.ensure_editable()

    def test_raises_once_no_show(self) -> None:
        appointment = _make_appointment()
        appointment.mark_no_show()
        with pytest.raises(AppointmentNotEditableError):
            appointment.ensure_editable()
