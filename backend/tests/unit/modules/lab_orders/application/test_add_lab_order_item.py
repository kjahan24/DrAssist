"""Unit tests for the `AddLabOrderItem` use case."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.clinical_notes.domain.exceptions import ClinicalNoteNotEditableError
from app.modules.lab_orders.application.dto import AddLabOrderItemInput
from app.modules.lab_orders.application.use_cases.add_lab_order_item import AddLabOrderItem
from app.modules.lab_orders.domain.entities import LabOrder
from app.modules.lab_orders.domain.events import LabOrderItemAdded
from app.modules.lab_orders.domain.exceptions import (
    LabOrderNotEditableError,
    LabOrderNotFoundError,
)
from tests.unit.modules.lab_orders.application.fakes import (
    FakeClinicalNoteQueryPort,
    FakeLabOrderItemRepository,
    FakeLabOrderRepository,
    FakeUnitOfWork,
    make_clinical_note_summary,
)


def _make_input(**overrides: object) -> AddLabOrderItemInput:
    defaults: dict[str, object] = {
        "lab_order_id": uuid4(),
        "test_code": "CBC",
        "test_name": "Complete Blood Count",
        "specimen_type": "Blood",
    }
    defaults.update(overrides)
    return AddLabOrderItemInput(**defaults)  # type: ignore[arg-type]


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
) -> AddLabOrderItem:
    return AddLabOrderItem(
        lab_order_repository=lab_order_repository,
        lab_order_item_repository=lab_order_item_repository,
        clinical_note_query_port=clinical_note_query_port,
        unit_of_work=unit_of_work,
    )


class TestAddLabOrderItem:
    async def test_adds_an_item_owned_by_the_given_lab_order(
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

        output = await use_case.execute(
            _make_input(lab_order_id=lab_order.id, test_name="Lipid Panel")
        )

        assert output.lab_order_id == lab_order.id
        stored = await lab_order_item_repository.get_by_id(output.lab_order_item_id)
        assert stored is not None
        assert stored.lab_order_id == lab_order.id
        assert stored.test_name == "Lipid Panel"
        assert unit_of_work.committed is True
        assert any(isinstance(e, LabOrderItemAdded) for e in unit_of_work.published_events)

    async def test_unknown_lab_order_raises(
        self,
        lab_order_repository: FakeLabOrderRepository,
        lab_order_item_repository: FakeLabOrderItemRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        port = FakeClinicalNoteQueryPort()
        use_case = _use_case(lab_order_repository, lab_order_item_repository, unit_of_work, port)

        with pytest.raises(LabOrderNotFoundError):
            await use_case.execute(_make_input(lab_order_id=uuid4()))

    async def test_adding_to_an_already_ordered_lab_order_raises(
        self,
        lab_order_repository: FakeLabOrderRepository,
        lab_order_item_repository: FakeLabOrderItemRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        clinical_note_id = uuid4()
        lab_order = _make_lab_order(clinical_note_id=clinical_note_id)
        lab_order.place_order()
        await lab_order_repository.add(lab_order)
        port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_id: make_clinical_note_summary(clinical_note_id=clinical_note_id)
            }
        )
        use_case = _use_case(lab_order_repository, lab_order_item_repository, unit_of_work, port)

        with pytest.raises(LabOrderNotEditableError):
            await use_case.execute(_make_input(lab_order_id=lab_order.id))

    async def test_adding_once_the_clinical_note_is_signed_raises(
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
            },
            not_editable={clinical_note_id},
        )
        use_case = _use_case(lab_order_repository, lab_order_item_repository, unit_of_work, port)

        with pytest.raises(ClinicalNoteNotEditableError):
            await use_case.execute(_make_input(lab_order_id=lab_order.id))

    async def test_multiple_items_can_be_added_to_the_same_lab_order(
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

        await use_case.execute(_make_input(lab_order_id=lab_order.id, test_name="CBC"))
        await use_case.execute(_make_input(lab_order_id=lab_order.id, test_name="Lipid Panel"))

        items = await lab_order_item_repository.list_by_lab_order(lab_order.id)
        assert {i.test_name for i in items} == {"CBC", "Lipid Panel"}
