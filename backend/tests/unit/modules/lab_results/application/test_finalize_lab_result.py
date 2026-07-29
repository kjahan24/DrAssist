"""Unit tests for the `FinalizeLabResult` use case — including "A Final
Lab Result must contain at least one Lab Result Item", the one invariant
in this module that spans two separate aggregates."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.lab_results.application.dto import FinalizeLabResultInput
from app.modules.lab_results.application.use_cases.finalize_lab_result import FinalizeLabResult
from app.modules.lab_results.domain.entities import LabResult, LabResultItem
from app.modules.lab_results.domain.enums import AbnormalFlag, LabResultStatus
from app.modules.lab_results.domain.events import LabResultFinalized
from app.modules.lab_results.domain.exceptions import (
    LabResultNotEditableError,
    LabResultNotFoundError,
    LabResultRequiresAtLeastOneItemError,
)
from tests.unit.modules.lab_results.application.fakes import (
    FakeLabResultItemRepository,
    FakeLabResultRepository,
    FakeUnitOfWork,
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


def _make_item(**overrides: object) -> LabResultItem:
    defaults: dict[str, object] = {
        "lab_result_id": uuid4(),
        "lab_order_item_id": uuid4(),
        "test_code": "CBC",
        "test_name": "Complete Blood Count",
        "result_value": "5.4",
        "abnormal_flag": AbnormalFlag.NORMAL,
    }
    defaults.update(overrides)
    return LabResultItem.create(**defaults)  # type: ignore[arg-type]


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
) -> FinalizeLabResult:
    return FinalizeLabResult(
        lab_result_repository=lab_result_repository,
        lab_result_item_repository=lab_result_item_repository,
        unit_of_work=unit_of_work,
    )


class TestFinalizeLabResult:
    async def test_finalizes_a_lab_result_with_at_least_one_item(
        self,
        lab_result_repository: FakeLabResultRepository,
        lab_result_item_repository: FakeLabResultItemRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        lab_result = _make_lab_result()
        await lab_result_repository.add(lab_result)
        await lab_result_item_repository.add(_make_item(lab_result_id=lab_result.id))
        use_case = _use_case(lab_result_repository, lab_result_item_repository, unit_of_work)

        output = await use_case.execute(FinalizeLabResultInput(lab_result_id=lab_result.id))

        assert output.status is LabResultStatus.FINAL
        stored = await lab_result_repository.get_by_id(lab_result.id)
        assert stored is not None
        assert stored.status is LabResultStatus.FINAL
        assert unit_of_work.committed is True
        assert any(isinstance(e, LabResultFinalized) for e in unit_of_work.published_events)

    async def test_finalizing_without_any_items_raises(
        self,
        lab_result_repository: FakeLabResultRepository,
        lab_result_item_repository: FakeLabResultItemRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        lab_result = _make_lab_result()
        await lab_result_repository.add(lab_result)
        use_case = _use_case(lab_result_repository, lab_result_item_repository, unit_of_work)

        with pytest.raises(LabResultRequiresAtLeastOneItemError):
            await use_case.execute(FinalizeLabResultInput(lab_result_id=lab_result.id))

    async def test_unknown_lab_result_raises(
        self,
        lab_result_repository: FakeLabResultRepository,
        lab_result_item_repository: FakeLabResultItemRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        use_case = _use_case(lab_result_repository, lab_result_item_repository, unit_of_work)

        with pytest.raises(LabResultNotFoundError):
            await use_case.execute(FinalizeLabResultInput(lab_result_id=uuid4()))

    async def test_finalizing_an_already_final_lab_result_raises(
        self,
        lab_result_repository: FakeLabResultRepository,
        lab_result_item_repository: FakeLabResultItemRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        lab_result = _make_lab_result()
        lab_result.finalize()
        await lab_result_repository.add(lab_result)
        await lab_result_item_repository.add(_make_item(lab_result_id=lab_result.id))
        use_case = _use_case(lab_result_repository, lab_result_item_repository, unit_of_work)

        with pytest.raises(LabResultNotEditableError):
            await use_case.execute(FinalizeLabResultInput(lab_result_id=lab_result.id))
