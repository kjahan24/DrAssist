"""Procedures module aggregate root: `VisitProcedure`.

A single aggregate for this foundation task. `VisitProcedure` is not
"owned by" the Visit module — like `VisitDiagnosis`, it references
`Visit` (`visit_id`) and, optionally, `Doctor` (`performed_by`) as peers,
each by ID only (never an object reference), validated by the
application layer via those modules' public `VisitQueryPort`/
`DoctorQueryPort` (see `application/use_cases/record_procedure.py`),
never by importing across `domain/` packages — see
`docs/backend-architecture/03_module_architecture.md`. Like
`VisitDiagnosis`, this is a one-to-many relationship: one visit can have
several procedures, distinguished by `sequence_number`.

No value object wraps `procedure_code`/`procedure_category`: neither has
a specified format or a cross-field invariant tying it to another field
(unlike `BloodPressure`'s systolic/diastolic pairing) — both are plain
nullable strings, the same reasoning
`app.modules.diagnosis.domain.entities` documents for `icd10_code`.

`procedure_status` follows a small workflow (`Planned` -> `In Progress`
-> `Completed`, with `Cancelled` as a side-branch reachable from any
state) shaped like `PatientVisit`'s own check-in/consultation/cancel
lifecycle, not `VisitDiagnosis`'s simpler two-way `confirm()`/`rule_out()`
— so it gets the same kind of dedicated transition methods
(`start()`/`complete()`/`cancel()`) `PatientVisit` uses, each enforcing
only the specific invariants this task's business rules actually state:
"performed_at is required only when status = Completed" (`complete()`
requires it as a parameter, so the invalid state can't be constructed)
and "Cancelled procedures cannot have performed_at" (`cancel()` clears
it, since a cancelled procedure retroactively has no performed time).
No other transition restriction is enforced — this task states none
(e.g. nothing forbids re-completing an already-cancelled procedure), and
inventing one would be scope creep.

All mutation goes through named methods that enforce the aggregate's
invariants and record domain events; nothing here performs I/O.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.procedures.domain.enums import ProcedureStatus
from app.modules.procedures.domain.events import (
    VisitProcedureRecorded,
    VisitProcedureStatusChanged,
    VisitProcedureUpdated,
)
from app.modules.procedures.domain.exceptions import (
    CancelledProcedureCannotHavePerformedAtError,
    InvalidSequenceNumberError,
    PerformedAtRequiredForCompletedProcedureError,
    ProcedureNameRequiredError,
)
from app.shared.domain.entity import AggregateRoot

_MIN_SEQUENCE_NUMBER = 1


@dataclass(kw_only=True, eq=False)
class VisitProcedure(AggregateRoot):
    organization_id: UUID
    visit_id: UUID
    sequence_number: int
    procedure_name: str
    procedure_code: str | None = None
    procedure_category: str | None = None
    procedure_status: ProcedureStatus = ProcedureStatus.PLANNED
    performed_by: UUID | None = None
    performed_at: datetime | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.procedure_name or not self.procedure_name.strip():
            raise ProcedureNameRequiredError()
        self.procedure_name = self.procedure_name.strip()
        _validate_sequence_number(self.sequence_number)
        _validate_status_performed_at_consistency(self.procedure_status, self.performed_at)

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        visit_id: UUID,
        sequence_number: int,
        procedure_name: str,
        procedure_code: str | None = None,
        procedure_category: str | None = None,
        procedure_status: ProcedureStatus = ProcedureStatus.PLANNED,
        performed_by: UUID | None = None,
        performed_at: datetime | None = None,
        notes: str | None = None,
    ) -> "VisitProcedure":
        procedure = cls(
            organization_id=organization_id,
            visit_id=visit_id,
            sequence_number=sequence_number,
            procedure_name=procedure_name,
            procedure_code=procedure_code,
            procedure_category=procedure_category,
            procedure_status=procedure_status,
            performed_by=performed_by,
            performed_at=performed_at,
            notes=notes,
        )
        procedure.record_event(
            VisitProcedureRecorded(
                procedure_id=procedure.id,
                organization_id=organization_id,
                visit_id=visit_id,
                sequence_number=procedure.sequence_number,
            )
        )
        return procedure

    def update_details(
        self,
        *,
        procedure_name: str | None = None,
        procedure_code: str | None = None,
        procedure_category: str | None = None,
        notes: str | None = None,
    ) -> None:
        """`sequence_number`, `procedure_status`, `performed_by`, and
        `performed_at` are deliberately not parameters here —
        `procedure_status` (and the `performed_at` it's coupled to)
        changes only through `start()`/`complete()`/`cancel()`, the same
        distinction `app.modules.diagnosis.domain.entities.VisitDiagnosis
        .update_details` draws by excluding its own status."""
        if procedure_name is not None:
            if not procedure_name.strip():
                raise ProcedureNameRequiredError()
            self.procedure_name = procedure_name.strip()
        if procedure_code is not None:
            self.procedure_code = procedure_code
        if procedure_category is not None:
            self.procedure_category = procedure_category
        if notes is not None:
            self.notes = notes

        self.touch()
        self.record_event(VisitProcedureUpdated(procedure_id=self.id, visit_id=self.visit_id))

    def start(self) -> None:
        self._set_status(ProcedureStatus.IN_PROGRESS)

    def complete(self, *, performed_at: datetime) -> None:
        self.procedure_status = ProcedureStatus.COMPLETED
        self.performed_at = performed_at
        self.touch()
        self.record_event(
            VisitProcedureStatusChanged(
                procedure_id=self.id, visit_id=self.visit_id, status=ProcedureStatus.COMPLETED.value
            )
        )

    def cancel(self) -> None:
        if self.procedure_status is ProcedureStatus.CANCELLED:
            return
        self.procedure_status = ProcedureStatus.CANCELLED
        self.performed_at = None
        self.touch()
        self.record_event(
            VisitProcedureStatusChanged(
                procedure_id=self.id, visit_id=self.visit_id, status=ProcedureStatus.CANCELLED.value
            )
        )

    def _set_status(self, status: ProcedureStatus) -> None:
        if self.procedure_status is status:
            return
        self.procedure_status = status
        self.touch()
        self.record_event(
            VisitProcedureStatusChanged(
                procedure_id=self.id, visit_id=self.visit_id, status=status.value
            )
        )


def _validate_sequence_number(value: int) -> None:
    if value < _MIN_SEQUENCE_NUMBER:
        raise InvalidSequenceNumberError(value)


def _validate_status_performed_at_consistency(
    status: ProcedureStatus, performed_at: datetime | None
) -> None:
    if status is ProcedureStatus.COMPLETED and performed_at is None:
        raise PerformedAtRequiredForCompletedProcedureError()
    if status is ProcedureStatus.CANCELLED and performed_at is not None:
        raise CancelledProcedureCannotHavePerformedAtError()
