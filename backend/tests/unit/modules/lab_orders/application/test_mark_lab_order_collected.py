"""Unit tests for the `MarkLabOrderCollected` use case."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.clinical_notes.domain.exceptions import ClinicalNoteNotEditableError
from app.modules.lab_orders.application.dto import MarkLabOrderCollectedInput
from app.modules.lab_orders.application.use_cases.mark_lab_order_collected import (
    MarkLabOrderCollected,
)
from app.modules.lab_orders.domain.entities import LabOrder
from app.modules.lab_orders.domain.enums import LabOrderStatus
from app.modules.lab_orders.domain.exceptions import (
    CollectionRequiresOrderedLabOrderError,
    LabOrderNotFoundError,
)
from tests.unit.modules.lab_orders.application.fakes import (
    FakeClinicalNoteQueryPort,
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
) -> MarkLabOrderCollected:
    return MarkLabOrderCollected(
        lab_order_repository=lab_order_repository,
        clinical_note_query_port=clinical_note_query_port,
        unit_of_work=unit_of_work,
    )


class TestMarkLabOrderCollected:
    async def test_marks_an_ordered_lab_order_as_collected(
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

        output = await use_case.execute(MarkLabOrderCollectedInput(lab_order_id=lab_order.id))

        assert output.status is LabOrderStatus.COLLECTED
        assert unit_of_work.committed is True

    async def test_marking_a_draft_lab_order_as_collected_raises(
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

        with pytest.raises(CollectionRequiresOrderedLabOrderError):
            await use_case.execute(MarkLabOrderCollectedInput(lab_order_id=lab_order.id))

    async def test_unknown_lab_order_raises(
        self, lab_order_repository: FakeLabOrderRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        port = FakeClinicalNoteQueryPort()
        use_case = _use_case(lab_order_repository, unit_of_work, port)

        with pytest.raises(LabOrderNotFoundError):
            await use_case.execute(MarkLabOrderCollectedInput(lab_order_id=uuid4()))

    async def test_marking_once_the_clinical_note_is_signed_raises(
        self, lab_order_repository: FakeLabOrderRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        clinical_note_id = uuid4()
        lab_order = _make_lab_order(clinical_note_id=clinical_note_id)
        lab_order.place_order()
        await lab_order_repository.add(lab_order)
        port = FakeClinicalNoteQueryPort(
            existing_notes={
                clinical_note_id: make_clinical_note_summary(clinical_note_id=clinical_note_id)
            },
            not_editable={clinical_note_id},
        )
        use_case = _use_case(lab_order_repository, unit_of_work, port)

        with pytest.raises(ClinicalNoteNotEditableError):
            await use_case.execute(MarkLabOrderCollectedInput(lab_order_id=lab_order.id))
