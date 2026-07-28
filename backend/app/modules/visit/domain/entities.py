"""Visit module aggregate root: `PatientVisit`.

A single aggregate for this foundation task — see
`app.modules.visit.container` for the module's scope note. Unlike the
Patient module's sub-resources (`PatientContact`, `PatientAllergy`, ...),
`PatientVisit` is not "owned by" a single other module — it references
both `Patient` (`patient_id`) and `Doctor` (`doctor_id`) as peers, each by
ID only (never an object reference), validated by the application layer
via those modules' public `PatientQueryPort`/`DoctorQueryPort` (see
`application/use_cases/schedule_visit.py`), never by importing across
`domain/` packages — see
`docs/backend-architecture/03_module_architecture.md`. All mutation goes
through named methods that enforce the aggregate's invariants and record
domain events; nothing here performs I/O.
"""

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

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
from app.shared.domain.entity import AggregateRoot


@dataclass(kw_only=True, eq=False)
class PatientVisit(AggregateRoot):
    organization_id: UUID
    patient_id: UUID
    doctor_id: UUID
    visit_number: str
    visit_type: VisitType
    visit_date: date
    appointment_id: UUID | None = None
    priority: VisitPriority = VisitPriority.NORMAL
    visit_status: VisitStatus = VisitStatus.SCHEDULED
    check_in_time: datetime | None = None
    consultation_start_time: datetime | None = None
    consultation_end_time: datetime | None = None
    check_out_time: datetime | None = None
    chief_complaint_summary: str | None = None
    reason_for_visit: str | None = None
    room_number: str | None = None
    follow_up_required: bool = False
    follow_up_date: date | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.visit_number or not self.visit_number.strip():
            raise VisitNumberRequiredError()
        self.visit_number = self.visit_number.strip()

        _validate_check_out_after_check_in(self.check_in_time, self.check_out_time)
        _validate_consultation_end_after_start(
            self.consultation_start_time, self.consultation_end_time
        )
        _validate_follow_up_date(self.follow_up_required, self.follow_up_date)

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        patient_id: UUID,
        doctor_id: UUID,
        visit_number: str,
        visit_type: VisitType,
        visit_date: date,
        appointment_id: UUID | None = None,
        priority: VisitPriority = VisitPriority.NORMAL,
        chief_complaint_summary: str | None = None,
        reason_for_visit: str | None = None,
        room_number: str | None = None,
        follow_up_required: bool = False,
        follow_up_date: date | None = None,
        notes: str | None = None,
    ) -> "PatientVisit":
        """A visit always starts `Scheduled`, with nothing checked in or
        consulted yet — `visit_status` and the check-in/consultation/
        check-out timestamps are therefore not constructor parameters;
        they're only ever set later via `check_in()`,
        `start_consultation()`, `complete()`, and `check_out()`.
        """
        visit = cls(
            organization_id=organization_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            visit_number=visit_number,
            visit_type=visit_type,
            visit_date=visit_date,
            appointment_id=appointment_id,
            priority=priority,
            chief_complaint_summary=chief_complaint_summary,
            reason_for_visit=reason_for_visit,
            room_number=room_number,
            follow_up_required=follow_up_required,
            follow_up_date=follow_up_date,
            notes=notes,
        )
        visit.record_event(
            PatientVisitScheduled(
                visit_id=visit.id,
                organization_id=organization_id,
                patient_id=patient_id,
                doctor_id=doctor_id,
                visit_number=visit.visit_number,
            )
        )
        return visit

    def update_details(
        self,
        *,
        visit_type: VisitType | None = None,
        priority: VisitPriority | None = None,
        visit_date: date | None = None,
        chief_complaint_summary: str | None = None,
        reason_for_visit: str | None = None,
        room_number: str | None = None,
        follow_up_required: bool | None = None,
        follow_up_date: date | None = None,
        notes: str | None = None,
    ) -> None:
        if visit_type is not None:
            self.visit_type = visit_type
        if priority is not None:
            self.priority = priority
        if visit_date is not None:
            self.visit_date = visit_date
        if chief_complaint_summary is not None:
            self.chief_complaint_summary = chief_complaint_summary
        if reason_for_visit is not None:
            self.reason_for_visit = reason_for_visit
        if room_number is not None:
            self.room_number = room_number
        if follow_up_required is not None or follow_up_date is not None:
            new_follow_up_required = (
                follow_up_required if follow_up_required is not None else self.follow_up_required
            )
            new_follow_up_date = (
                follow_up_date if follow_up_date is not None else self.follow_up_date
            )
            _validate_follow_up_date(new_follow_up_required, new_follow_up_date)
            self.follow_up_required = new_follow_up_required
            self.follow_up_date = new_follow_up_date
        if notes is not None:
            self.notes = notes

        self.touch()
        self.record_event(PatientVisitUpdated(visit_id=self.id, patient_id=self.patient_id))

    def check_in(self, *, check_in_time: datetime) -> None:
        _validate_check_out_after_check_in(check_in_time, self.check_out_time)
        self.visit_status = VisitStatus.CHECKED_IN
        self.check_in_time = check_in_time
        self.touch()
        self.record_event(
            PatientVisitCheckedIn(
                visit_id=self.id, patient_id=self.patient_id, check_in_time=check_in_time
            )
        )

    def start_consultation(self, *, consultation_start_time: datetime) -> None:
        if self.visit_status is VisitStatus.COMPLETED:
            raise CompletedVisitCannotReturnToInProgressError()
        _validate_consultation_end_after_start(consultation_start_time, self.consultation_end_time)
        self.visit_status = VisitStatus.IN_PROGRESS
        self.consultation_start_time = consultation_start_time
        self.touch()
        self.record_event(
            PatientVisitConsultationStarted(
                visit_id=self.id,
                patient_id=self.patient_id,
                consultation_start_time=consultation_start_time,
            )
        )

    def complete(self, *, consultation_end_time: datetime) -> None:
        _validate_consultation_end_after_start(self.consultation_start_time, consultation_end_time)
        self.visit_status = VisitStatus.COMPLETED
        self.consultation_end_time = consultation_end_time
        self.touch()
        self.record_event(
            PatientVisitCompleted(
                visit_id=self.id,
                patient_id=self.patient_id,
                consultation_end_time=consultation_end_time,
            )
        )

    def check_out(self, *, check_out_time: datetime) -> None:
        _validate_check_out_after_check_in(self.check_in_time, check_out_time)
        self.check_out_time = check_out_time
        self.touch()
        self.record_event(
            PatientVisitCheckedOut(
                visit_id=self.id, patient_id=self.patient_id, check_out_time=check_out_time
            )
        )

    def cancel(self) -> None:
        self._set_status(VisitStatus.CANCELLED)

    def mark_no_show(self) -> None:
        self._set_status(VisitStatus.NO_SHOW)

    def _set_status(self, status: VisitStatus) -> None:
        if self.visit_status is status:
            return
        self.visit_status = status
        self.touch()
        self.record_event(
            PatientVisitStatusChanged(
                visit_id=self.id, patient_id=self.patient_id, status=status.value
            )
        )


def _validate_check_out_after_check_in(
    check_in_time: datetime | None, check_out_time: datetime | None
) -> None:
    if check_in_time is not None and check_out_time is not None and check_out_time < check_in_time:
        raise CheckOutBeforeCheckInError()


def _validate_consultation_end_after_start(
    consultation_start_time: datetime | None, consultation_end_time: datetime | None
) -> None:
    if (
        consultation_start_time is not None
        and consultation_end_time is not None
        and consultation_end_time < consultation_start_time
    ):
        raise ConsultationEndBeforeStartError()


def _validate_follow_up_date(follow_up_required: bool, follow_up_date: date | None) -> None:
    if follow_up_required and follow_up_date is None:
        raise FollowUpDateRequiredError()
