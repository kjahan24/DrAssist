"""Unit tests for the `LabOrder` aggregate's own invariants: its
Draft -> Ordered -> Collected workflow, `Cancelled` reachable from Draft
or Ordered, and the "own status must be Draft" self-check
`ensure_editable()` shares with `update_details()`/`place_order()`.

The cross-aggregate "must have at least one item" check has no
domain-layer test here — it is enforced by `PlaceLabOrder` (see
`tests/unit/modules/lab_orders/application/test_place_lab_order.py`), not
by `LabOrder.place_order()` itself.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.lab_orders.domain.entities import LabOrder
from app.modules.lab_orders.domain.enums import LabOrderStatus, Priority
from app.modules.lab_orders.domain.events import (
    LabOrderCreated,
    LabOrderStatusChanged,
    LabOrderUpdated,
)
from app.modules.lab_orders.domain.exceptions import (
    CollectionRequiresOrderedLabOrderError,
    LabOrderCannotBeCancelledError,
    LabOrderNotEditableError,
    OrderNumberRequiredError,
)


def _make_lab_order(**overrides: object) -> LabOrder:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "clinical_note_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_id": uuid4(),
        "order_number": "LAB-0001",
        "ordered_at": datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
    }
    defaults.update(overrides)
    return LabOrder.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_create_sets_identity_fields_and_records_event(self) -> None:
        organization_id = uuid4()
        clinical_note_id = uuid4()
        patient_id = uuid4()
        visit_id = uuid4()
        doctor_id = uuid4()

        lab_order = _make_lab_order(
            organization_id=organization_id,
            clinical_note_id=clinical_note_id,
            patient_id=patient_id,
            visit_id=visit_id,
            doctor_id=doctor_id,
        )

        assert lab_order.organization_id == organization_id
        assert lab_order.clinical_note_id == clinical_note_id
        assert lab_order.patient_id == patient_id
        assert lab_order.visit_id == visit_id
        assert lab_order.doctor_id == doctor_id
        events = lab_order.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], LabOrderCreated)
        assert events[0].lab_order_id == lab_order.id
        assert events[0].clinical_note_id == clinical_note_id

    def test_default_status_is_draft(self) -> None:
        assert _make_lab_order().status is LabOrderStatus.DRAFT

    def test_default_priority_is_routine(self) -> None:
        assert _make_lab_order().priority is Priority.ROUTINE

    def test_blank_order_number_is_rejected(self) -> None:
        with pytest.raises(OrderNumberRequiredError):
            _make_lab_order(order_number="   ")

    def test_order_number_is_stripped(self) -> None:
        lab_order = _make_lab_order(order_number="  LAB-0002  ")
        assert lab_order.order_number == "LAB-0002"


class TestUpdateDetails:
    def test_update_changes_fields_and_records_event_while_draft(self) -> None:
        lab_order = _make_lab_order()
        lab_order.pull_events()

        lab_order.update_details(priority=Priority.STAT, notes="Fasting required")

        assert lab_order.priority is Priority.STAT
        assert lab_order.notes == "Fasting required"
        events = lab_order.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], LabOrderUpdated)

    def test_update_leaves_unspecified_fields_unchanged(self) -> None:
        lab_order = _make_lab_order(notes="Original notes")
        lab_order.update_details(priority=Priority.URGENT)
        assert lab_order.notes == "Original notes"

    def test_update_once_ordered_is_rejected(self) -> None:
        lab_order = _make_lab_order()
        lab_order.place_order()
        with pytest.raises(LabOrderNotEditableError):
            lab_order.update_details(notes="New notes")


class TestPlaceOrder:
    def test_place_order_sets_status_and_records_event(self) -> None:
        lab_order = _make_lab_order()
        lab_order.pull_events()

        lab_order.place_order()

        assert lab_order.status is LabOrderStatus.ORDERED
        events = lab_order.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], LabOrderStatusChanged)
        assert events[0].status == "ordered"

    def test_placing_an_already_ordered_order_is_rejected(self) -> None:
        lab_order = _make_lab_order()
        lab_order.place_order()
        with pytest.raises(LabOrderNotEditableError):
            lab_order.place_order()

    def test_placing_a_cancelled_order_is_rejected(self) -> None:
        lab_order = _make_lab_order()
        lab_order.cancel()
        with pytest.raises(LabOrderNotEditableError):
            lab_order.place_order()


class TestMarkCollected:
    def test_mark_collected_from_ordered_sets_status_and_records_event(self) -> None:
        lab_order = _make_lab_order()
        lab_order.place_order()
        lab_order.pull_events()

        lab_order.mark_collected()

        assert lab_order.status is LabOrderStatus.COLLECTED
        events = lab_order.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], LabOrderStatusChanged)
        assert events[0].status == "collected"

    def test_mark_collected_from_draft_is_rejected(self) -> None:
        lab_order = _make_lab_order()
        with pytest.raises(CollectionRequiresOrderedLabOrderError):
            lab_order.mark_collected()

    def test_mark_collected_from_cancelled_is_rejected(self) -> None:
        lab_order = _make_lab_order()
        lab_order.cancel()
        with pytest.raises(CollectionRequiresOrderedLabOrderError):
            lab_order.mark_collected()

    def test_mark_collected_twice_is_rejected(self) -> None:
        lab_order = _make_lab_order()
        lab_order.place_order()
        lab_order.mark_collected()
        with pytest.raises(CollectionRequiresOrderedLabOrderError):
            lab_order.mark_collected()


class TestCancel:
    def test_cancel_from_draft_sets_status_and_records_event(self) -> None:
        lab_order = _make_lab_order()
        lab_order.pull_events()

        lab_order.cancel()

        assert lab_order.status is LabOrderStatus.CANCELLED
        events = lab_order.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], LabOrderStatusChanged)
        assert events[0].status == "cancelled"

    def test_cancel_from_ordered_is_accepted(self) -> None:
        lab_order = _make_lab_order()
        lab_order.place_order()

        lab_order.cancel()

        assert lab_order.status is LabOrderStatus.CANCELLED

    def test_cancel_from_collected_is_rejected(self) -> None:
        lab_order = _make_lab_order()
        lab_order.place_order()
        lab_order.mark_collected()
        with pytest.raises(LabOrderCannotBeCancelledError):
            lab_order.cancel()

    def test_cancel_twice_is_rejected(self) -> None:
        lab_order = _make_lab_order()
        lab_order.cancel()
        with pytest.raises(LabOrderCannotBeCancelledError):
            lab_order.cancel()


class TestEnsureEditable:
    def test_does_not_raise_while_draft(self) -> None:
        _make_lab_order().ensure_editable()

    def test_raises_once_ordered(self) -> None:
        lab_order = _make_lab_order()
        lab_order.place_order()
        with pytest.raises(LabOrderNotEditableError):
            lab_order.ensure_editable()
