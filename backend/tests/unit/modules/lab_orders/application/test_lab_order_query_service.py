"""Unit tests for `LabOrderQueryService` — backs the module's public
`LabOrderQueryPort` facade."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.lab_orders.application.services.lab_order_query_service import (
    LabOrderQueryService,
)
from app.modules.lab_orders.domain.entities import LabOrder, LabOrderItem
from tests.unit.modules.lab_orders.application.fakes import (
    FakeLabOrderItemRepository,
    FakeLabOrderRepository,
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
def lab_order_repo() -> FakeLabOrderRepository:
    return FakeLabOrderRepository()


@pytest.fixture
def item_repo() -> FakeLabOrderItemRepository:
    return FakeLabOrderItemRepository()


@pytest.fixture
def service(
    lab_order_repo: FakeLabOrderRepository, item_repo: FakeLabOrderItemRepository
) -> LabOrderQueryService:
    return LabOrderQueryService(
        lab_order_repository=lab_order_repo, lab_order_item_repository=item_repo
    )


class TestLabOrderExists:
    async def test_true_for_a_known_lab_order(
        self, service: LabOrderQueryService, lab_order_repo: FakeLabOrderRepository
    ) -> None:
        lab_order = _make_lab_order()
        await lab_order_repo.add(lab_order)
        assert await service.lab_order_exists(lab_order.id) is True

    async def test_false_for_an_unknown_lab_order(self, service: LabOrderQueryService) -> None:
        assert await service.lab_order_exists(uuid4()) is False


class TestIsEditable:
    async def test_true_while_draft(
        self, service: LabOrderQueryService, lab_order_repo: FakeLabOrderRepository
    ) -> None:
        lab_order = _make_lab_order()
        await lab_order_repo.add(lab_order)
        assert await service.is_editable(lab_order.id) is True

    async def test_false_once_ordered(
        self, service: LabOrderQueryService, lab_order_repo: FakeLabOrderRepository
    ) -> None:
        lab_order = _make_lab_order()
        lab_order.place_order()
        await lab_order_repo.add(lab_order)
        assert await service.is_editable(lab_order.id) is False

    async def test_false_once_cancelled(
        self, service: LabOrderQueryService, lab_order_repo: FakeLabOrderRepository
    ) -> None:
        lab_order = _make_lab_order()
        lab_order.cancel()
        await lab_order_repo.add(lab_order)
        assert await service.is_editable(lab_order.id) is False

    async def test_false_for_an_unknown_lab_order(self, service: LabOrderQueryService) -> None:
        assert await service.is_editable(uuid4()) is False


class TestGetLabOrderSummary:
    async def test_returns_summary_with_items(
        self,
        service: LabOrderQueryService,
        lab_order_repo: FakeLabOrderRepository,
        item_repo: FakeLabOrderItemRepository,
    ) -> None:
        lab_order = _make_lab_order(notes="Fasting required")
        await lab_order_repo.add(lab_order)
        await item_repo.add(_make_item(lab_order_id=lab_order.id, test_name="CBC"))
        await item_repo.add(_make_item(lab_order_id=lab_order.id, test_name="Lipid Panel"))

        summary = await service.get_lab_order_summary(lab_order.id)

        assert summary is not None
        assert summary.lab_order_id == lab_order.id
        assert summary.organization_id == lab_order.organization_id
        assert summary.patient_id == lab_order.patient_id
        assert summary.visit_id == lab_order.visit_id
        assert summary.doctor_id == lab_order.doctor_id
        assert summary.notes == "Fasting required"
        assert {i.test_name for i in summary.items} == {"CBC", "Lipid Panel"}

    async def test_returns_none_for_an_unknown_lab_order(
        self, service: LabOrderQueryService
    ) -> None:
        assert await service.get_lab_order_summary(uuid4()) is None


class TestListLabOrdersForClinicalNote:
    async def test_returns_orders_scoped_to_the_clinical_note(
        self, service: LabOrderQueryService, lab_order_repo: FakeLabOrderRepository
    ) -> None:
        clinical_note_id = uuid4()
        await lab_order_repo.add(
            _make_lab_order(clinical_note_id=clinical_note_id, order_number="LAB-A")
        )
        await lab_order_repo.add(
            _make_lab_order(clinical_note_id=clinical_note_id, order_number="LAB-B")
        )
        await lab_order_repo.add(_make_lab_order(order_number="LAB-OTHER"))

        summaries = await service.list_lab_orders_for_clinical_note(clinical_note_id)

        assert {s.order_number for s in summaries} == {"LAB-A", "LAB-B"}

    async def test_returns_empty_list_for_a_clinical_note_without_orders(
        self, service: LabOrderQueryService
    ) -> None:
        assert await service.list_lab_orders_for_clinical_note(uuid4()) == []


class TestListLabOrdersForPatient:
    async def test_returns_orders_scoped_to_the_patient(
        self, service: LabOrderQueryService, lab_order_repo: FakeLabOrderRepository
    ) -> None:
        patient_id = uuid4()
        await lab_order_repo.add(_make_lab_order(patient_id=patient_id, order_number="LAB-A"))
        await lab_order_repo.add(_make_lab_order(order_number="LAB-B"))

        summaries = await service.list_lab_orders_for_patient(patient_id)

        assert [s.order_number for s in summaries] == ["LAB-A"]

    async def test_returns_empty_list_for_a_patient_without_orders(
        self, service: LabOrderQueryService
    ) -> None:
        assert await service.list_lab_orders_for_patient(uuid4()) == []
