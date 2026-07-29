"""Unit tests for the `PlaceLabOrder` use case — including "Ordered Lab
Orders must contain at least one Lab Order Item", the one invariant in
this module that spans two separate aggregates."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.clinical_notes.domain.exceptions import ClinicalNoteNotEditableError
from app.modules.lab_orders.application.dto import PlaceLabOrderInput
from app.modules.lab_orders.application.use_cases.place_lab_order import PlaceLabOrder
from app.modules.lab_orders.domain.entities import LabOrder, LabOrderItem
from app.modules.lab_orders.domain.enums import LabOrderStatus
from app.modules.lab_orders.domain.events import LabOrderStatusChanged
from app.modules.lab_orders.domain.exceptions import (
    LabOrderNotEditableError,
    LabOrderNotFoundError,
    LabOrderRequiresAtLeastOneItemError,
)
from tests.unit.modules.lab_orders.application.fakes import (
    FakeClinicalNoteQueryPort,
    FakeLabOrderItemRepository,
    FakeLabOrderRepository,
    FakeUnitOfWork,
    make_clinical_note_summary,
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


def _make_item(**overrides: object) -> LabOrderItem:
    defaults: dict[str, object] = {
        "lab_order_id": uuid4(),
        "test_code": "CBC",
        "test_name": "Complete Blood Count",
        "specimen_type": "Blood",
    }
    defaults.update(overrides)
    return LabOrderItem.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def lab_order_repository() -> FakeLabOrderRepository:
    return FakeLabOrderRepository()


@pytest.fixture
def lab_order_item_repository() -> FakeLabOrderItemRepository:
    return FakeLabOrderItemRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    lab_order_repository: FakeLabOrderRepository,
    lab_order_item_repository: FakeLabOrderItemRepository,
    unit_of_work: FakeUnitOfWork,
    clinical_note_query_port: FakeClinicalNoteQueryPort,
) -> PlaceLabOrder:
    return PlaceLabOrder(
        lab_order_repository=lab_order_repository,
        lab_order_item_repository=lab_order_item_repository,
        clinical_note_query_port=clinical_note_query_port,
        unit_of_work=unit_of_work,
    )


class TestPlaceLabOrder:
    async def test_places_a_lab_order_with_at_least_one_item(
        self,
        lab_order_repository: FakeLabOrderRepository,
        lab_order_item_repository: FakeLabOrderItemRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        clinical_note_id = uuid4()
        lab_order = _make_lab_order(clinical_note_id=clinical_note_id)
        await lab_order_repository.add(lab_order)
        await lab_order_item_repository.add(_make_item(lab_order_id=lab_order.id))
        port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_id: make_clinical_note_summary(clinical_note_id=clinical_note_id)
            }
        )
        use_case = _use_case(lab_order_repository, lab_order_item_repository, unit_of_work, port)

        output = await use_case.execute(PlaceLabOrderInput(lab_order_id=lab_order.id))

        assert output.status is LabOrderStatus.ORDERED
        stored = await lab_order_repository.get_by_id(lab_order.id)
        assert stored is not None
        assert stored.status is LabOrderStatus.ORDERED
        assert unit_of_work.committed is True
        assert any(isinstance(e, LabOrderStatusChanged) for e in unit_of_work.published_events)

    async def test_placing_without_any_items_raises(
        self,
        lab_order_repository: FakeLabOrderRepository,
        lab_order_item_repository: FakeLabOrderItemRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        clinical_note_id = uuid4()
        lab_order = _make_lab_order(clinical_note_id=clinical_note_id)
        await lab_order_repository.add(lab_order)
        port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_id: make_clinical_note_summary(clinical_note_id=clinical_note_id)
            }
        )
        use_case = _use_case(lab_order_repository, lab_order_item_repository, unit_of_work, port)

        with pytest.raises(LabOrderRequiresAtLeastOneItemError):
            await use_case.execute(PlaceLabOrderInput(lab_order_id=lab_order.id))

    async def test_unknown_lab_order_raises(
        self,
        lab_order_repository: FakeLabOrderRepository,
        lab_order_item_repository: FakeLabOrderItemRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        port = FakeClinicalNoteQueryPort()
        use_case = _use_case(lab_order_repository, lab_order_item_repository, unit_of_work, port)

        with pytest.raises(LabOrderNotFoundError):
            await use_case.execute(PlaceLabOrderInput(lab_order_id=uuid4()))

    async def test_placing_once_the_clinical_note_is_signed_raises(
        self,
        lab_order_repository: FakeLabOrderRepository,
        lab_order_item_repository: FakeLabOrderItemRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        clinical_note_id = uuid4()
        lab_order = _make_lab_order(clinical_note_id=clinical_note_id)
        await lab_order_repository.add(lab_order)
        await lab_order_item_repository.add(_make_item(lab_order_id=lab_order.id))
        port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_id: make_clinical_note_summary(clinical_note_id=clinical_note_id)
            },
            not_editable={clinical_note_id},
        )
        use_case = _use_case(lab_order_repository, lab_order_item_repository, unit_of_work, port)

        with pytest.raises(ClinicalNoteNotEditableError):
            await use_case.execute(PlaceLabOrderInput(lab_order_id=lab_order.id))

    async def test_placing_an_already_ordered_lab_order_raises(
        self,
        lab_order_repository: FakeLabOrderRepository,
        lab_order_item_repository: FakeLabOrderItemRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        clinical_note_id = uuid4()
        lab_order = _make_lab_order(clinical_note_id=clinical_note_id)
        lab_order.place_order()
        await lab_order_repository.add(lab_order)
        await lab_order_item_repository.add(_make_item(lab_order_id=lab_order.id))
        port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_id: make_clinical_note_summary(clinical_note_id=clinical_note_id)
            }
        )
        use_case = _use_case(lab_order_repository, lab_order_item_repository, unit_of_work, port)

        with pytest.raises(LabOrderNotEditableError):
            await use_case.execute(PlaceLabOrderInput(lab_order_id=lab_order.id))
