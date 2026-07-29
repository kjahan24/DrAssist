"""Unit tests for the `LabResult` aggregate's own invariants: its
Draft -> Final transition and the "own status must be Draft" self-check
`ensure_editable()` shares with `update_details()`/`finalize()`.

The cross-aggregate "must have at least one item" check has no
domain-layer test here — it is enforced by `FinalizeLabResult` (see
`tests/unit/modules/lab_results/application/test_finalize_lab_result.py`),
not by `LabResult.finalize()` itself.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.lab_results.domain.entities import LabResult
from app.modules.lab_results.domain.enums import LabResultStatus
from app.modules.lab_results.domain.events import (
    LabResultCreated,
    LabResultFinalized,
    LabResultUpdated,
)
from app.modules.lab_results.domain.exceptions import (
    LabResultNotEditableError,
    ResultNumberRequiredError,
)


def _make_lab_result(**overrides: object) -> LabResult:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "lab_order_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "result_number": "RES-0001",
        "reported_at": datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
    }
    defaults.update(overrides)
    return LabResult.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_sets_identity_fields_and_records_event(self) -> None:
        organization_id = uuid4()
        lab_order_id = uuid4()
        patient_id = uuid4()
        visit_id = uuid4()
        doctor_id = uuid4()

        lab_result = _make_lab_result(
            organization_id=organization_id,
            lab_order_id=lab_order_id,
            patient_id=patient_id,
            visit_id=visit_id,
            doctor_id=doctor_id,
        )

        assert lab_result.organization_id == organization_id
        assert lab_result.lab_order_id == lab_order_id
        assert lab_result.patient_id == patient_id
        assert lab_result.visit_id == visit_id
        assert lab_result.doctor_id == doctor_id
        events = lab_result.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], LabResultCreated)
        assert events[0].lab_result_id == lab_result.id
        assert events[0].lab_order_id == lab_order_id

    def test_default_status_is_draft(self) -> None:
        assert _make_lab_result().status is LabResultStatus.DRAFT

    def test_blank_result_number_is_rejected(self) -> None:
        with pytest.raises(ResultNumberRequiredError):
            _make_lab_result(result_number="   ")

    def test_result_number_is_stripped(self) -> None:
        lab_result = _make_lab_result(result_number="  RES-0002  ")
        assert lab_result.result_number == "RES-0002"


class TestUpdateDetails:
    def test_update_changes_fields_and_records_event_while_draft(self) -> None:
        lab_result = _make_lab_result()
        lab_result.pull_events()

        lab_result.update_details(laboratory_name="Acme Labs", comments="Sample hemolyzed")

        assert lab_result.laboratory_name == "Acme Labs"
        assert lab_result.comments == "Sample hemolyzed"
        events = lab_result.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], LabResultUpdated)

    def test_update_leaves_unspecified_fields_unchanged(self) -> None:
        lab_result = _make_lab_result(comments="Original comments")
        lab_result.update_details(laboratory_name="Acme Labs")
        assert lab_result.comments == "Original comments"

    def test_update_once_final_is_rejected(self) -> None:
        lab_result = _make_lab_result()
        lab_result.finalize()
        with pytest.raises(LabResultNotEditableError):
            lab_result.update_details(comments="New comments")


class TestFinalize:
    def test_finalize_sets_status_and_records_event(self) -> None:
        lab_result = _make_lab_result()
        lab_result.pull_events()

        lab_result.finalize()

        assert lab_result.status is LabResultStatus.FINAL
        events = lab_result.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], LabResultFinalized)
        assert events[0].lab_result_id == lab_result.id

    def test_finalizing_an_already_final_lab_result_is_rejected(self) -> None:
        lab_result = _make_lab_result()
        lab_result.finalize()
        with pytest.raises(LabResultNotEditableError):
            lab_result.finalize()


class TestEnsureEditable:
    def test_does_not_raise_while_draft(self) -> None:
        _make_lab_result().ensure_editable()

    def test_raises_once_final(self) -> None:
        lab_result = _make_lab_result()
        lab_result.finalize()
        with pytest.raises(LabResultNotEditableError):
            lab_result.ensure_editable()
