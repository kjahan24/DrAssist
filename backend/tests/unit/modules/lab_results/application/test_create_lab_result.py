"""Unit tests for the `CreateLabResult` use case, using in-memory fakes
for both this module's own repository and the Lab Orders module's public
port."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.lab_results.application.dto import CreateLabResultInput
from app.modules.lab_results.application.use_cases.create_lab_result import CreateLabResult
from app.modules.lab_results.domain.events import LabResultCreated
from app.modules.lab_results.domain.exceptions import (
    DuplicateLabResultError,
    DuplicateResultNumberError,
    LabOrderNotFoundError,
)
from tests.unit.modules.lab_results.application.fakes import (
    FakeLabOrderQueryPort,
    FakeLabResultRepository,
    FakeUnitOfWork,
    make_lab_order_summary,
)


def _make_input(**overrides: object) -> CreateLabResultInput:
    defaults: dict[str, object] = {
        "lab_order_id": uuid4(),
        "result_number": "RES-0001",
        "reported_at": datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
    }
    defaults.update(overrides)
    return CreateLabResultInput(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def lab_result_repository() -> FakeLabResultRepository:
    return FakeLabResultRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    lab_result_repository: FakeLabResultRepository,
    unit_of_work: FakeUnitOfWork,
    lab_order_query_port: FakeLabOrderQueryPort,
) -> CreateLabResult:
    return CreateLabResult(
        lab_result_repository=lab_result_repository,
        lab_order_query_port=lab_order_query_port,
        unit_of_work=unit_of_work,
    )


class TestCreateLabResult:
    async def test_creates_a_lab_result_deriving_identity_from_the_lab_order(
        self, lab_result_repository: FakeLabResultRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        lab_order_id = uuid4()
        organization_id = uuid4()
        patient_id = uuid4()
        visit_id = uuid4()
        doctor_id = uuid4()
        summary = make_lab_order_summary(
            lab_order_id=lab_order_id,
            organization_id=organization_id,
            patient_id=patient_id,
            visit_id=visit_id,
            doctor_id=doctor_id,
        )
        port = FakeLabOrderQueryPort(existing_orders={lab_order_id: summary})
        use_case = _use_case(lab_result_repository, unit_of_work, port)

        output = await use_case.execute(
            _make_input(lab_order_id=lab_order_id, laboratory_name="Acme Labs")
        )

        stored = await lab_result_repository.get_by_id(output.lab_result_id)
        assert stored is not None
        assert stored.organization_id == organization_id
        assert stored.patient_id == patient_id
        assert stored.visit_id == visit_id
        assert stored.doctor_id == doctor_id
        assert stored.laboratory_name == "Acme Labs"
        assert unit_of_work.committed is True
        assert any(isinstance(e, LabResultCreated) for e in unit_of_work.published_events)

    async def test_unknown_lab_order_raises(
        self, lab_result_repository: FakeLabResultRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        port = FakeLabOrderQueryPort()
        use_case = _use_case(lab_result_repository, unit_of_work, port)

        with pytest.raises(LabOrderNotFoundError):
            await use_case.execute(_make_input(lab_order_id=uuid4()))

    async def test_a_second_lab_result_for_the_same_lab_order_raises(
        self, lab_result_repository: FakeLabResultRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        lab_order_id = uuid4()
        summary = make_lab_order_summary(lab_order_id=lab_order_id)
        port = FakeLabOrderQueryPort(existing_orders={lab_order_id: summary})
        use_case = _use_case(lab_result_repository, unit_of_work, port)
        await use_case.execute(_make_input(lab_order_id=lab_order_id))

        with pytest.raises(DuplicateLabResultError):
            await use_case.execute(_make_input(lab_order_id=lab_order_id))

    async def test_duplicate_result_number_across_different_orders_raises(
        self, lab_result_repository: FakeLabResultRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        lab_order_a = uuid4()
        lab_order_b = uuid4()
        port = FakeLabOrderQueryPort(
            existing_orders={
                lab_order_a: make_lab_order_summary(lab_order_id=lab_order_a),
                lab_order_b: make_lab_order_summary(lab_order_id=lab_order_b),
            }
        )
        use_case = _use_case(lab_result_repository, unit_of_work, port)
        await use_case.execute(_make_input(lab_order_id=lab_order_a, result_number="RES-SHARED"))

        with pytest.raises(DuplicateResultNumberError):
            await use_case.execute(
                _make_input(lab_order_id=lab_order_b, result_number="RES-SHARED")
            )
