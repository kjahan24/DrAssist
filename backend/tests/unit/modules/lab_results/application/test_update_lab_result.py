"""Unit tests for the `UpdateLabResult` use case. No cross-module port is
constructed at all — see `domain/entities.py` for why this module never
checks the parent lab order's editability."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.lab_results.application.dto import UpdateLabResultInput
from app.modules.lab_results.application.use_cases.update_lab_result import UpdateLabResult
from app.modules.lab_results.domain.entities import LabResult
from app.modules.lab_results.domain.events import LabResultUpdated
from app.modules.lab_results.domain.exceptions import (
    LabResultNotEditableError,
    LabResultNotFoundError,
)
from tests.unit.modules.lab_results.application.fakes import (
    FakeLabResultRepository,
    FakeUnitOfWork,
)


def _make_input(**overrides: object) -> UpdateLabResultInput:
    defaults: dict[str, object] = {"lab_result_id": uuid4()}
    defaults.update(overrides)
    return UpdateLabResultInput(**defaults)  # type: ignore[arg-type]


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
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    lab_result_repository: FakeLabResultRepository, unit_of_work: FakeUnitOfWork
) -> UpdateLabResult:
    return UpdateLabResult(lab_result_repository=lab_result_repository, unit_of_work=unit_of_work)


class TestUpdateLabResult:
    async def test_updates_fields_while_draft(
        self, lab_result_repository: FakeLabResultRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        lab_result = _make_lab_result()
        await lab_result_repository.add(lab_result)
        use_case = _use_case(lab_result_repository, unit_of_work)

        output = await use_case.execute(
            _make_input(lab_result_id=lab_result.id, comments="Revised comments")
        )

        stored = await lab_result_repository.get_by_id(output.lab_result_id)
        assert stored is not None
        assert stored.comments == "Revised comments"
        assert unit_of_work.committed is True
        assert any(isinstance(e, LabResultUpdated) for e in unit_of_work.published_events)

    async def test_unknown_lab_result_raises(
        self, lab_result_repository: FakeLabResultRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        use_case = _use_case(lab_result_repository, unit_of_work)

        with pytest.raises(LabResultNotFoundError):
            await use_case.execute(_make_input(lab_result_id=uuid4()))

    async def test_updating_an_already_final_lab_result_raises(
        self, lab_result_repository: FakeLabResultRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        lab_result = _make_lab_result()
        lab_result.finalize()
        await lab_result_repository.add(lab_result)
        use_case = _use_case(lab_result_repository, unit_of_work)

        with pytest.raises(LabResultNotEditableError):
            await use_case.execute(_make_input(lab_result_id=lab_result.id, comments="New"))
