"""Unit tests for the `PatientVisit` aggregate's invariants."""

from datetime import date, datetime, timedelta
from uuid import uuid4

import pytest

from app.modules.visit.domain.entities import PatientVisit
from app.modules.visit.domain.enums import VisitPriority, VisitStatus, VisitType
from app.modules.visit.domain.events import (
    PatientVisitCheckedIn,
    PatientVisitCheckedOut,
    PatientVisitCompleted,
    PatientVisitConsultationStarted,
    PatientVisitScheduled,
    PatientVisitStatusChanged,
    PatientVisitUpdated,
)
from app.modules.visit.domain.exceptions import (
    CheckOutBeforeCheckInError,
    CompletedVisitCannotReturnToInProgressError,
    ConsultationEndBeforeStartError,
    FollowUpDateRequiredError,
    VisitNumberRequiredError,
)


def _make_visit(**overrides: object) -> PatientVisit:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "doctor_id": uuid4(),
        "visit_number": "V-0001",
        "visit_type": VisitType.CONSULTATION,
        "visit_date": date(2026, 1, 1),
    }
    defaults.update(overrides)
    return PatientVisit.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_records_patient_visit_scheduled_event(self) -> None:
        patient_id = uuid4()
        doctor_id = uuid4()
        visit = _make_visit(patient_id=patient_id, doctor_id=doctor_id)

        assert visit.patient_id == patient_id
        assert visit.doctor_id == doctor_id
        assert visit.visit_status is VisitStatus.SCHEDULED
        assert visit.priority is VisitPriority.NORMAL
        events = visit.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PatientVisitScheduled)
        assert events[0].visit_number == "V-0001"

    def test_blank_visit_number_is_rejected(self) -> None:
        with pytest.raises(VisitNumberRequiredError):
            _make_visit(visit_number="   ")

    def test_visit_number_is_stripped(self) -> None:
        visit = _make_visit(visit_number="  V-0002  ")
        assert visit.visit_number == "V-0002"

    def test_no_check_in_or_consultation_timestamps_at_creation(self) -> None:
        visit = _make_visit()
        assert visit.check_in_time is None
        assert visit.consultation_start_time is None
        assert visit.consultation_end_time is None
        assert visit.check_out_time is None

    def test_follow_up_required_without_follow_up_date_is_rejected(self) -> None:
        with pytest.raises(FollowUpDateRequiredError):
            _make_visit(follow_up_required=True, follow_up_date=None)

    def test_follow_up_required_with_follow_up_date_is_accepted(self) -> None:
        visit = _make_visit(follow_up_required=True, follow_up_date=date(2026, 2, 1))
        assert visit.follow_up_date == date(2026, 2, 1)

    def test_follow_up_not_required_without_follow_up_date_is_accepted(self) -> None:
        visit = _make_visit(follow_up_required=False, follow_up_date=None)
        assert visit.follow_up_date is None


class TestUpdateDetails:
    def test_update_changes_fields_and_records_event(self) -> None:
        visit = _make_visit()
        visit.pull_events()

        visit.update_details(priority=VisitPriority.URGENT, room_number="12B")

        assert visit.priority is VisitPriority.URGENT
        assert visit.room_number == "12B"
        events = visit.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PatientVisitUpdated)

    def test_update_follow_up_required_without_date_is_rejected(self) -> None:
        visit = _make_visit()
        with pytest.raises(FollowUpDateRequiredError):
            visit.update_details(follow_up_required=True)

    def test_update_follow_up_required_and_date_together_is_accepted(self) -> None:
        visit = _make_visit()
        visit.update_details(follow_up_required=True, follow_up_date=date(2026, 2, 1))
        assert visit.follow_up_required is True
        assert visit.follow_up_date == date(2026, 2, 1)

    def test_update_leaves_unspecified_fields_unchanged(self) -> None:
        visit = _make_visit(reason_for_visit="Annual checkup")
        visit.update_details(room_number="5A")
        assert visit.reason_for_visit == "Annual checkup"


class TestCheckInAndCheckOut:
    def test_check_in_sets_status_and_time_and_records_event(self) -> None:
        visit = _make_visit()
        visit.pull_events()
        check_in_time = datetime(2026, 1, 1, 9, 0)

        visit.check_in(check_in_time=check_in_time)

        assert visit.visit_status is VisitStatus.CHECKED_IN
        assert visit.check_in_time == check_in_time
        events = visit.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PatientVisitCheckedIn)

    def test_check_out_sets_time_and_records_event(self) -> None:
        visit = _make_visit()
        check_in_time = datetime(2026, 1, 1, 9, 0)
        visit.check_in(check_in_time=check_in_time)
        visit.pull_events()

        check_out_time = check_in_time + timedelta(hours=1)
        visit.check_out(check_out_time=check_out_time)

        assert visit.check_out_time == check_out_time
        events = visit.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PatientVisitCheckedOut)

    def test_check_out_before_check_in_is_rejected(self) -> None:
        visit = _make_visit()
        check_in_time = datetime(2026, 1, 1, 9, 0)
        visit.check_in(check_in_time=check_in_time)

        with pytest.raises(CheckOutBeforeCheckInError):
            visit.check_out(check_out_time=check_in_time - timedelta(minutes=1))

    def test_check_out_equal_to_check_in_is_accepted(self) -> None:
        visit = _make_visit()
        check_in_time = datetime(2026, 1, 1, 9, 0)
        visit.check_in(check_in_time=check_in_time)
        visit.check_out(check_out_time=check_in_time)
        assert visit.check_out_time == check_in_time


class TestConsultationLifecycle:
    def test_start_consultation_sets_status_and_time_and_records_event(self) -> None:
        visit = _make_visit()
        visit.pull_events()
        start_time = datetime(2026, 1, 1, 9, 15)

        visit.start_consultation(consultation_start_time=start_time)

        assert visit.visit_status is VisitStatus.IN_PROGRESS
        assert visit.consultation_start_time == start_time
        events = visit.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PatientVisitConsultationStarted)

    def test_complete_sets_status_and_time_and_records_event(self) -> None:
        visit = _make_visit()
        start_time = datetime(2026, 1, 1, 9, 15)
        visit.start_consultation(consultation_start_time=start_time)
        visit.pull_events()

        end_time = start_time + timedelta(minutes=20)
        visit.complete(consultation_end_time=end_time)

        assert visit.visit_status is VisitStatus.COMPLETED
        assert visit.consultation_end_time == end_time
        events = visit.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PatientVisitCompleted)

    def test_consultation_end_before_start_is_rejected(self) -> None:
        visit = _make_visit()
        start_time = datetime(2026, 1, 1, 9, 15)
        visit.start_consultation(consultation_start_time=start_time)

        with pytest.raises(ConsultationEndBeforeStartError):
            visit.complete(consultation_end_time=start_time - timedelta(minutes=1))

    def test_completed_visit_cannot_return_to_in_progress(self) -> None:
        visit = _make_visit()
        start_time = datetime(2026, 1, 1, 9, 15)
        visit.start_consultation(consultation_start_time=start_time)
        visit.complete(consultation_end_time=start_time + timedelta(minutes=20))

        with pytest.raises(CompletedVisitCannotReturnToInProgressError):
            visit.start_consultation(consultation_start_time=start_time + timedelta(hours=1))


class TestCancelAndNoShow:
    def test_cancel_sets_status_and_records_event(self) -> None:
        visit = _make_visit()
        visit.pull_events()

        visit.cancel()

        assert visit.visit_status is VisitStatus.CANCELLED
        events = visit.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PatientVisitStatusChanged)
        assert events[0].status == "cancelled"

    def test_mark_no_show_sets_status_and_records_event(self) -> None:
        visit = _make_visit()
        visit.pull_events()

        visit.mark_no_show()

        assert visit.visit_status is VisitStatus.NO_SHOW
        events = visit.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], PatientVisitStatusChanged)
        assert events[0].status == "no_show"

    def test_cancelling_an_already_cancelled_visit_is_idempotent(self) -> None:
        visit = _make_visit()
        visit.cancel()
        visit.pull_events()
        visit.cancel()
        assert visit.pull_events() == []
