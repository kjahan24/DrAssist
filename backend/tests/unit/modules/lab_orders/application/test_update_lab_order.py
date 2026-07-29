"""Unit tests for the `UpdateLabOrder` use case — both the cross-module
read-only enforcement (Clinical Note Signed/Locked) and the own-aggregate
read-only enforcement (LabOrder no longer Draft)."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.clinical_notes.domain.exceptions import ClinicalNoteNotEditableError
from app.modules.lab_orders.application.dto import UpdateLabOrderInput
from app.modules.lab_orders.application.use_cases.update_lab_order import UpdateLabOrder
from app.modules.lab_orders.domain.entities import LabOrder
from app.modules.lab_orders.domain.enums import Priority
from app.modules.lab_orders.domain.events import LabOrderUpdated
from app.modules.lab_orders.domain.exceptions import (
    LabOrderNotEditableError,
    LabOrderNotFoundError,
)
from tests.unit.modules.lab_orders.application.fakes import (
    FakeClinicalNoteQueryPort,
    FakeLabOrderRepository,
    FakeUnitOfWork,
    make_clinical_note_summary,
)


def _make_input(**overrides: object) -> UpdateLabOrderInput:
    defaults: dict[str, object] = {"lab_order_id": uuid4()}
    defaults.update(overrides)
    return UpdateLabOrderInput(**defaults)  # type: ignore[arg-type]


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
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    lab_order_repository: FakeLabOrderRepository,
    unit_of_work: FakeUnitOfWork,
    clinical_note_query_port: FakeClinicalNoteQueryPort,
) -> UpdateLabOrder:
    return UpdateLabOrder(
        lab_order_repository=lab_order_repository,
        clinical_note_query_port=clinical_note_query_port,
        unit_of_work=unit_of_work,
    )


class TestUpdateLabOrder:
    async def test_updates_fields_when_the_clinical_note_is_editable(
        self, lab_order_repository: FakeLabOrderRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        lab_order = _make_lab_order(clinical_note_id=clinical_note_id)
        await lab_order_repository.add(lab_order)
        port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_id: make_clinical_note_summary(clinical_note_id=clinical_note_id)
            }
        )
        use_case = _use_case(lab_order_repository, unit_of_work, port)

        output = await use_case.execute(
            _make_input(lab_order_id=lab_order.id, priority=Priority.URGENT)
        )

        stored = await lab_order_repository.get_by_id(output.lab_order_id)
        assert stored is not None
        assert stored.priority is Priority.URGENT
        assert unit_of_work.committed is True
        assert any(isinstance(e, LabOrderUpdated) for e in unit_of_work.published_events)

    async def test_unknown_lab_order_raises(
        self, lab_order_repository: FakeLabOrderRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        port = FakeClinicalNoteQueryPort()
        use_case = _use_case(lab_order_repository, unit_of_work, port)

        with pytest.raises(LabOrderNotFoundError):
            await use_case.execute(_make_input(lab_order_id=uuid4()))

    async def test_updating_once_the_clinical_note_is_signed_raises(
        self, lab_order_repository: FakeLabOrderRepository, unit_of_work: FakeUnitOfWork
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
        use_case = _use_case(lab_order_repository, unit_of_work, port)

        with pytest.raises(ClinicalNoteNotEditableError):
            await use_case.execute(_make_input(lab_order_id=lab_order.id, notes="New"))

    async def test_updating_an_already_ordered_lab_order_raises(
        self, lab_order_repository: FakeLabOrderRepository, unit_of_work: FakeUnitOfWork
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
        use_case = _use_case(lab_order_repository, unit_of_work, port)

        with pytest.raises(LabOrderNotEditableError):
            await use_case.execute(_make_input(lab_order_id=lab_order.id, notes="New"))
