"""Unit tests for the `VisitProcedure` aggregate's invariants."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.modules.procedures.domain.entities import VisitProcedure
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


def _make_procedure(**overrides: object) -> VisitProcedure:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "visit_id": uuid4(),
        "sequence_number": 1,
        "procedure_name": "Wound dressing",
    }
    defaults.update(overrides)
    return VisitProcedure.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_records_visit_procedure_recorded_event(self) -> None:
        organization_id = uuid4()
        visit_id = uuid4()
        procedure = _make_procedure(organization_id=organization_id, visit_id=visit_id)

        assert procedure.organization_id == organization_id
        assert procedure.visit_id == visit_id
        events = procedure.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], VisitProcedureRecorded)

    def test_blank_procedure_name_is_rejected(self) -> None:
        with pytest.raises(ProcedureNameRequiredError):
            _make_procedure(procedure_name="   ")

    def test_procedure_name_is_stripped(self) -> None:
        procedure = _make_procedure(procedure_name="  Suturing  ")
        assert procedure.procedure_name == "Suturing"

    @pytest.mark.parametrize("value", [0, -1])
    def test_sequence_number_below_one_is_rejected(self, value: int) -> None:
        with pytest.raises(InvalidSequenceNumberError):
            _make_procedure(sequence_number=value)

    def test_sequence_number_of_one_is_accepted(self) -> None:
        procedure = _make_procedure(sequence_number=1)
        assert procedure.sequence_number == 1

    def test_default_status_is_planned(self) -> None:
        procedure = _make_procedure()
        assert procedure.procedure_status is ProcedureStatus.PLANNED

    def test_default_performed_at_is_none(self) -> None:
        procedure = _make_procedure()
        assert procedure.performed_at is None

    def test_completed_without_performed_at_at_creation_is_rejected(self) -> None:
        with pytest.raises(PerformedAtRequiredForCompletedProcedureError):
            _make_procedure(procedure_status=ProcedureStatus.COMPLETED, performed_at=None)

    def test_completed_with_performed_at_at_creation_is_accepted(self) -> None:
        performed_at = datetime(2026, 1, 1, 9, 0)
        procedure = _make_procedure(
            procedure_status=ProcedureStatus.COMPLETED, performed_at=performed_at
        )
        assert procedure.performed_at == performed_at

    def test_cancelled_with_performed_at_at_creation_is_rejected(self) -> None:
        with pytest.raises(CancelledProcedureCannotHavePerformedAtError):
            _make_procedure(
                procedure_status=ProcedureStatus.CANCELLED,
                performed_at=datetime(2026, 1, 1, 9, 0),
            )

    def test_cancelled_without_performed_at_at_creation_is_accepted(self) -> None:
        procedure = _make_procedure(procedure_status=ProcedureStatus.CANCELLED, performed_at=None)
        assert procedure.performed_at is None

    def test_planned_with_performed_at_is_accepted(self) -> None:
        """No rule forbids a non-terminal status from carrying
        `performed_at` — only `Completed` (requires it) and `Cancelled`
        (forbids it) are constrained."""
        performed_at = datetime(2026, 1, 1, 9, 0)
        procedure = _make_procedure(
            procedure_status=ProcedureStatus.PLANNED, performed_at=performed_at
        )
        assert procedure.performed_at == performed_at


class TestUpdateDetails:
    def test_update_changes_fields_and_records_event(self) -> None:
        procedure = _make_procedure()
        procedure.pull_events()

        procedure.update_details(notes="Performed under local anesthesia")

        assert procedure.notes == "Performed under local anesthesia"
        events = procedure.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], VisitProcedureUpdated)

    def test_update_leaves_unspecified_fields_unchanged(self) -> None:
        procedure = _make_procedure(procedure_code="P-001")
        procedure.update_details(notes="Reviewed")
        assert procedure.procedure_code == "P-001"

    def test_update_with_blank_procedure_name_is_rejected(self) -> None:
        procedure = _make_procedure()
        with pytest.raises(ProcedureNameRequiredError):
            procedure.update_details(procedure_name="   ")


class TestStart:
    def test_start_sets_status_and_records_event(self) -> None:
        procedure = _make_procedure()
        procedure.pull_events()

        procedure.start()

        assert procedure.procedure_status is ProcedureStatus.IN_PROGRESS
        events = procedure.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], VisitProcedureStatusChanged)
        assert events[0].status == "in_progress"

    def test_starting_an_already_in_progress_procedure_is_idempotent(self) -> None:
        procedure = _make_procedure()
        procedure.start()
        procedure.pull_events()
        procedure.start()
        assert procedure.pull_events() == []


class TestComplete:
    def test_complete_sets_status_and_performed_at_and_records_event(self) -> None:
        procedure = _make_procedure()
        procedure.pull_events()
        performed_at = datetime(2026, 1, 1, 10, 0)

        procedure.complete(performed_at=performed_at)

        assert procedure.procedure_status is ProcedureStatus.COMPLETED
        assert procedure.performed_at == performed_at
        events = procedure.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], VisitProcedureStatusChanged)
        assert events[0].status == "completed"


class TestCancel:
    def test_cancel_sets_status_and_clears_performed_at_and_records_event(self) -> None:
        procedure = _make_procedure()
        procedure.start()
        procedure.pull_events()

        procedure.cancel()

        assert procedure.procedure_status is ProcedureStatus.CANCELLED
        assert procedure.performed_at is None
        events = procedure.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], VisitProcedureStatusChanged)
        assert events[0].status == "cancelled"

    def test_cancelling_a_completed_procedure_clears_performed_at(self) -> None:
        procedure = _make_procedure()
        procedure.complete(performed_at=datetime(2026, 1, 1, 10, 0))

        procedure.cancel()

        assert procedure.procedure_status is ProcedureStatus.CANCELLED
        assert procedure.performed_at is None

    def test_cancelling_an_already_cancelled_procedure_is_idempotent(self) -> None:
        procedure = _make_procedure()
        procedure.cancel()
        procedure.pull_events()
        procedure.cancel()
        assert procedure.pull_events() == []
