"""Unit tests for the `AddLabResultItem` use case, including "Every Lab
Result Item must reference an existing Lab Order Item" — the invariant
unique to this module."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.lab_results.application.dto import AddLabResultItemInput
from app.modules.lab_results.application.use_cases.add_lab_result_item import AddLabResultItem
from app.modules.lab_results.domain.entities import LabResult
from app.modules.lab_results.domain.enums import AbnormalFlag
from app.modules.lab_results.domain.events import LabResultItemAdded
from app.modules.lab_results.domain.exceptions import (
    InvalidLabOrderItemReferenceError,
    LabResultNotEditableError,
    LabResultNotFoundError,
)
from tests.unit.modules.lab_results.application.fakes import (
    FakeLabOrderQueryPort,
    FakeLabResultItemRepository,
    FakeLabResultRepository,
    FakeUnitOfWork,
    make_lab_order_item_summary,
    make_lab_order_summary,
)


def _make_input(**overrides: object) -> AddLabResultItemInput:
    defaults: dict[str, object] = {
        "lab_result_id": uuid4(),
        "lab_order_item_id": uuid4(),
        "test_code": "CBC",
        "test_name": "Complete Blood Count",
        "result_value": "5.4",
        "abnormal_flag": AbnormalFlag.NORMAL,
    }
    defaults.update(overrides)
    return AddLabResultItemInput(**defaults)  # type: ignore[arg-type]


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


@pytest.fixture
def lab_result_repository() -> FakeLabResultRepository:
    return FakeLabResultRepository()


@pytest.fixture
def lab_result_item_repository() -> FakeLabResultItemRepository:
    return FakeLabResultItemRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    lab_result_repository: FakeLabResultRepository,
    lab_result_item_repository: FakeLabResultItemRepository,
    unit_of_work: FakeUnitOfWork,
    lab_order_query_port: FakeLabOrderQueryPort,
) -> AddLabResultItem:
    return AddLabResultItem(
        lab_result_repository=lab_result_repository,
        lab_result_item_repository=lab_result_item_repository,
        lab_order_query_port=lab_order_query_port,
        unit_of_work=unit_of_work,
    )


class TestAddLabResultItem:
    async def test_adds_an_item_referencing_a_valid_lab_order_item(
        self,
        lab_result_repository: FakeLabResultRepository,
        lab_result_item_repository: FakeLabResultItemRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        lab_order_id = uuid4()
        lab_order_item_id = uuid4()
        lab_result = _make_lab_result(lab_order_id=lab_order_id)
        await lab_result_repository.add(lab_result)
        lab_order_summary = make_lab_order_summary(
            lab_order_id=lab_order_id,
            items=[
                make_lab_order_item_summary(
                    lab_order_item_id=lab_order_item_id, lab_order_id=lab_order_id
                )
            ],
        )
        port = FakeLabOrderQueryPort(existing_orders={lab_order_id: lab_order_summary})
        use_case = _use_case(lab_result_repository, lab_result_item_repository, unit_of_work, port)

        output = await use_case.execute(
            _make_input(
                lab_result_id=lab_result.id,
                lab_order_item_id=lab_order_item_id,
                test_name="Hemoglobin",
            )
        )

        assert output.lab_result_id == lab_result.id
        stored = await lab_result_item_repository.get_by_id(output.lab_result_item_id)
        assert stored is not None
        assert stored.lab_result_id == lab_result.id
        assert stored.lab_order_item_id == lab_order_item_id
        assert stored.test_name == "Hemoglobin"
        assert unit_of_work.committed is True
        assert any(isinstance(e, LabResultItemAdded) for e in unit_of_work.published_events)

    async def test_unknown_lab_result_raises(
        self,
        lab_result_repository: FakeLabResultRepository,
        lab_result_item_repository: FakeLabResultItemRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        port = FakeLabOrderQueryPort()
        use_case = _use_case(lab_result_repository, lab_result_item_repository, unit_of_work, port)

        with pytest.raises(LabResultNotFoundError):
            await use_case.execute(_make_input(lab_result_id=uuid4()))

    async def test_referencing_a_lab_order_item_from_a_different_lab_order_raises(
        self,
        lab_result_repository: FakeLabResultRepository,
        lab_result_item_repository: FakeLabResultItemRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        lab_order_id = uuid4()
        lab_result = _make_lab_result(lab_order_id=lab_order_id)
        await lab_result_repository.add(lab_result)
        # The lab order has one real item, but the caller references a
        # completely different (unknown) lab_order_item_id.
        lab_order_summary = make_lab_order_summary(
            lab_order_id=lab_order_id,
            items=[make_lab_order_item_summary(lab_order_id=lab_order_id)],
        )
        port = FakeLabOrderQueryPort(existing_orders={lab_order_id: lab_order_summary})
        use_case = _use_case(lab_result_repository, lab_result_item_repository, unit_of_work, port)

        with pytest.raises(InvalidLabOrderItemReferenceError):
            await use_case.execute(
                _make_input(lab_result_id=lab_result.id, lab_order_item_id=uuid4())
            )

    async def test_adding_to_an_already_final_lab_result_raises(
        self,
        lab_result_repository: FakeLabResultRepository,
        lab_result_item_repository: FakeLabResultItemRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        lab_order_id = uuid4()
        lab_order_item_id = uuid4()
        lab_result = _make_lab_result(lab_order_id=lab_order_id)
        lab_result.finalize()
        await lab_result_repository.add(lab_result)
        lab_order_summary = make_lab_order_summary(
            lab_order_id=lab_order_id,
            items=[
                make_lab_order_item_summary(
                    lab_order_item_id=lab_order_item_id, lab_order_id=lab_order_id
                )
            ],
        )
        port = FakeLabOrderQueryPort(existing_orders={lab_order_id: lab_order_summary})
        use_case = _use_case(lab_result_repository, lab_result_item_repository, unit_of_work, port)

        with pytest.raises(LabResultNotEditableError):
            await use_case.execute(
                _make_input(lab_result_id=lab_result.id, lab_order_item_id=lab_order_item_id)
            )
