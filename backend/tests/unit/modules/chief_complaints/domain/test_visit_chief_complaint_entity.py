"""Unit tests for the `VisitChiefComplaint` aggregate's invariants."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.modules.chief_complaints.domain.entities import VisitChiefComplaint
from app.modules.chief_complaints.domain.enums import DurationUnit, Onset, Severity
from app.modules.chief_complaints.domain.events import (
    VisitChiefComplaintRecorded,
    VisitChiefComplaintUpdated,
)
from app.modules.chief_complaints.domain.exceptions import (
    ComplaintRequiredError,
    DurationUnitRequiresDurationValueError,
    InvalidSequenceNumberError,
    NegativeDurationValueError,
)


def _make_chief_complaint(**overrides: object) -> VisitChiefComplaint:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "visit_id": uuid4(),
        "sequence_number": 1,
        "complaint": "Persistent cough",
        "recorded_at": datetime(2026, 1, 1, 9, 0),
    }
    defaults.update(overrides)
    return VisitChiefComplaint.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_records_visit_chief_complaint_recorded_event(self) -> None:
        organization_id = uuid4()
        visit_id = uuid4()
        chief_complaint = _make_chief_complaint(organization_id=organization_id, visit_id=visit_id)

        assert chief_complaint.organization_id == organization_id
        assert chief_complaint.visit_id == visit_id
        events = chief_complaint.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], VisitChiefComplaintRecorded)

    def test_blank_complaint_is_rejected(self) -> None:
        with pytest.raises(ComplaintRequiredError):
            _make_chief_complaint(complaint="   ")

    def test_complaint_is_stripped(self) -> None:
        chief_complaint = _make_chief_complaint(complaint="  Headache  ")
        assert chief_complaint.complaint == "Headache"

    @pytest.mark.parametrize("value", [0, -1])
    def test_sequence_number_below_one_is_rejected(self, value: int) -> None:
        with pytest.raises(InvalidSequenceNumberError):
            _make_chief_complaint(sequence_number=value)

    def test_sequence_number_of_one_is_accepted(self) -> None:
        chief_complaint = _make_chief_complaint(sequence_number=1)
        assert chief_complaint.sequence_number == 1

    def test_negative_duration_value_is_rejected(self) -> None:
        with pytest.raises(NegativeDurationValueError):
            _make_chief_complaint(duration_value=-1)

    def test_duration_unit_without_duration_value_is_rejected(self) -> None:
        with pytest.raises(DurationUnitRequiresDurationValueError):
            _make_chief_complaint(duration_unit=DurationUnit.DAYS)

    def test_duration_value_without_duration_unit_is_accepted(self) -> None:
        """The business rule is one-directional ("duration_unit is
        allowed only when duration_value exists") — the reverse isn't
        forbidden, the same shape `PatientVisit.follow_up_required`/
        `follow_up_date` already establishes."""
        chief_complaint = _make_chief_complaint(duration_value=3, duration_unit=None)
        assert chief_complaint.duration_value == 3
        assert chief_complaint.duration_unit is None

    def test_duration_value_and_unit_together_are_accepted(self) -> None:
        chief_complaint = _make_chief_complaint(duration_value=3, duration_unit=DurationUnit.DAYS)
        assert chief_complaint.duration_value == 3
        assert chief_complaint.duration_unit is DurationUnit.DAYS

    def test_severity_and_onset_are_optional(self) -> None:
        chief_complaint = _make_chief_complaint()
        assert chief_complaint.severity is None
        assert chief_complaint.onset is None

    def test_severity_and_onset_are_stored(self) -> None:
        chief_complaint = _make_chief_complaint(severity=Severity.MODERATE, onset=Onset.GRADUAL)
        assert chief_complaint.severity is Severity.MODERATE
        assert chief_complaint.onset is Onset.GRADUAL


class TestUpdateDetails:
    def test_update_changes_fields_and_records_event(self) -> None:
        chief_complaint = _make_chief_complaint()
        chief_complaint.pull_events()

        chief_complaint.update_details(severity=Severity.SEVERE, notes="Worsening overnight")

        assert chief_complaint.severity is Severity.SEVERE
        assert chief_complaint.notes == "Worsening overnight"
        events = chief_complaint.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], VisitChiefComplaintUpdated)

    def test_update_leaves_unspecified_fields_unchanged(self) -> None:
        chief_complaint = _make_chief_complaint(onset=Onset.SUDDEN)
        chief_complaint.update_details(severity=Severity.MILD)
        assert chief_complaint.onset is Onset.SUDDEN

    def test_update_with_blank_complaint_is_rejected(self) -> None:
        chief_complaint = _make_chief_complaint()
        with pytest.raises(ComplaintRequiredError):
            chief_complaint.update_details(complaint="   ")

    def test_update_duration_unit_without_existing_or_new_duration_value_is_rejected(
        self,
    ) -> None:
        chief_complaint = _make_chief_complaint()
        with pytest.raises(DurationUnitRequiresDurationValueError):
            chief_complaint.update_details(duration_unit=DurationUnit.WEEKS)

    def test_update_duration_value_and_unit_together_is_accepted(self) -> None:
        chief_complaint = _make_chief_complaint()
        chief_complaint.update_details(duration_value=2, duration_unit=DurationUnit.WEEKS)
        assert chief_complaint.duration_value == 2
        assert chief_complaint.duration_unit is DurationUnit.WEEKS

    def test_update_duration_unit_alone_is_accepted_when_value_already_set(self) -> None:
        chief_complaint = _make_chief_complaint(duration_value=5)
        chief_complaint.update_details(duration_unit=DurationUnit.HOURS)
        assert chief_complaint.duration_value == 5
        assert chief_complaint.duration_unit is DurationUnit.HOURS
