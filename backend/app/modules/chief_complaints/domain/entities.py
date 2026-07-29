"""Chief Complaints module aggregate root: `VisitChiefComplaint`.

A single aggregate for this foundation task. `VisitChiefComplaint` is not
"owned by" the Visit module — like `VisitVitalSigns`, it references
`Visit` (`visit_id`) and, optionally, `Doctor` (`recorded_by`) as peers,
each by ID only (never an object reference), validated by the
application layer via those modules' public `VisitQueryPort`/
`DoctorQueryPort` (see
`application/use_cases/record_chief_complaint.py`), never by importing
across `domain/` packages — see
`docs/backend-architecture/03_module_architecture.md`. Unlike
`VisitVitalSigns`, this is a one-to-many relationship: one visit can have
several chief complaints, distinguished by `sequence_number`. All
mutation goes through named methods that enforce the aggregate's
invariants and record domain events; nothing here performs I/O.

No value object wraps `duration_value`/`duration_unit`: the one business
rule linking them ("duration_unit is allowed only when duration_value
exists") is one-directional, the same shape as `PatientVisit`'s
`follow_up_required`/`follow_up_date` pair — which the Visit module
likewise validates with a plain function rather than a value object (see
`app.modules.visit.domain.entities._validate_follow_up_date`). A value
object earns its place by guaranteeing a *mutual* invariant (like
`BloodPressure`'s systolic/diastolic pairing); a one-directional "X
requires Y" rule doesn't need one.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

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
from app.shared.domain.entity import AggregateRoot

_MIN_SEQUENCE_NUMBER = 1


@dataclass(kw_only=True, eq=False)
class VisitChiefComplaint(AggregateRoot):
    organization_id: UUID
    visit_id: UUID
    sequence_number: int
    complaint: str
    recorded_at: datetime
    duration_value: int | None = None
    duration_unit: DurationUnit | None = None
    severity: Severity | None = None
    onset: Onset | None = None
    notes: str | None = None
    recorded_by: UUID | None = None

    def __post_init__(self) -> None:
        if not self.complaint or not self.complaint.strip():
            raise ComplaintRequiredError()
        self.complaint = self.complaint.strip()
        _validate_sequence_number(self.sequence_number)
        _validate_duration(self.duration_value, self.duration_unit)

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        visit_id: UUID,
        sequence_number: int,
        complaint: str,
        recorded_at: datetime,
        duration_value: int | None = None,
        duration_unit: DurationUnit | None = None,
        severity: Severity | None = None,
        onset: Onset | None = None,
        notes: str | None = None,
        recorded_by: UUID | None = None,
    ) -> "VisitChiefComplaint":
        chief_complaint = cls(
            organization_id=organization_id,
            visit_id=visit_id,
            sequence_number=sequence_number,
            complaint=complaint,
            recorded_at=recorded_at,
            duration_value=duration_value,
            duration_unit=duration_unit,
            severity=severity,
            onset=onset,
            notes=notes,
            recorded_by=recorded_by,
        )
        chief_complaint.record_event(
            VisitChiefComplaintRecorded(
                chief_complaint_id=chief_complaint.id,
                organization_id=organization_id,
                visit_id=visit_id,
                sequence_number=chief_complaint.sequence_number,
            )
        )
        return chief_complaint

    def update_details(
        self,
        *,
        complaint: str | None = None,
        duration_value: int | None = None,
        duration_unit: DurationUnit | None = None,
        severity: Severity | None = None,
        onset: Onset | None = None,
        notes: str | None = None,
    ) -> None:
        """`sequence_number`, `recorded_by`, and `recorded_at` are
        deliberately not parameters here — they identify *when and by
        whom* the complaint was recorded, not details of the complaint
        itself, the same distinction `PatientVisit.update_details`
        draws by excluding `visit_number`/timestamps."""
        if complaint is not None:
            if not complaint.strip():
                raise ComplaintRequiredError()
            self.complaint = complaint.strip()
        if duration_value is not None or duration_unit is not None:
            new_duration_value = (
                duration_value if duration_value is not None else self.duration_value
            )
            new_duration_unit = duration_unit if duration_unit is not None else self.duration_unit
            _validate_duration(new_duration_value, new_duration_unit)
            self.duration_value = new_duration_value
            self.duration_unit = new_duration_unit
        if severity is not None:
            self.severity = severity
        if onset is not None:
            self.onset = onset
        if notes is not None:
            self.notes = notes

        self.touch()
        self.record_event(
            VisitChiefComplaintUpdated(chief_complaint_id=self.id, visit_id=self.visit_id)
        )


def _validate_sequence_number(value: int) -> None:
    if value < _MIN_SEQUENCE_NUMBER:
        raise InvalidSequenceNumberError(value)


def _validate_duration(duration_value: int | None, duration_unit: DurationUnit | None) -> None:
    if duration_value is not None and duration_value < 0:
        raise NegativeDurationValueError(duration_value)
    if duration_unit is not None and duration_value is None:
        raise DurationUnitRequiresDurationValueError()
