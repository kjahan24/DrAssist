"""Unit tests for `LabResultQueryService` — backs the module's public
`LabResultQueryPort` facade."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.lab_results.application.services.lab_result_query_service import (
    LabResultQueryService,
)
from app.modules.lab_results.domain.entities import LabResult, LabResultItem
from app.modules.lab_results.domain.enums import AbnormalFlag
from tests.unit.modules.lab_results.application.fakes import (
    FakeLabResultItemRepository,
    FakeLabResultRepository,
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
def lab_result_repo() -> FakeLabResultRepository:
    return FakeLabResultRepository()


@pytest.fixture
def item_repo() -> FakeLabResultItemRepository:
    return FakeLabResultItemRepository()


@pytest.fixture
def service(
    lab_result_repo: FakeLabResultRepository, item_repo: FakeLabResultItemRepository
) -> LabResultQueryService:
    return LabResultQueryService(
        lab_result_repository=lab_result_repo, lab_result_item_repository=item_repo
    )


class TestLabResultExistsForLabOrder:
    async def test_true_for_a_known_lab_order(
        self, service: LabResultQueryService, lab_result_repo: FakeLabResultRepository
    ) -> None:
        lab_result = _make_lab_result()
        await lab_result_repo.add(lab_result)
        assert await service.lab_result_exists_for_lab_order(lab_result.lab_order_id) is True

    async def test_false_for_an_unknown_lab_order(self, service: LabResultQueryService) -> None:
        assert await service.lab_result_exists_for_lab_order(uuid4()) is False


class TestIsEditable:
    async def test_true_while_draft(
        self, service: LabResultQueryService, lab_result_repo: FakeLabResultRepository
    ) -> None:
        lab_result = _make_lab_result()
        await lab_result_repo.add(lab_result)
        assert await service.is_editable(lab_result.lab_order_id) is True

    async def test_false_once_final(
        self, service: LabResultQueryService, lab_result_repo: FakeLabResultRepository
    ) -> None:
        lab_result = _make_lab_result()
        lab_result.finalize()
        await lab_result_repo.add(lab_result)
        assert await service.is_editable(lab_result.lab_order_id) is False

    async def test_false_for_an_unknown_lab_order(self, service: LabResultQueryService) -> None:
        assert await service.is_editable(uuid4()) is False


class TestGetLabResultSummary:
    async def test_returns_summary_with_items(
        self,
        service: LabResultQueryService,
        lab_result_repo: FakeLabResultRepository,
        item_repo: FakeLabResultItemRepository,
    ) -> None:
        lab_result = _make_lab_result(comments="Sample hemolyzed")
        await lab_result_repo.add(lab_result)
        await item_repo.add(_make_item(lab_result_id=lab_result.id, test_name="CBC"))
        await item_repo.add(_make_item(lab_result_id=lab_result.id, test_name="Lipid Panel"))

        summary = await service.get_lab_result_summary(lab_result.lab_order_id)

        assert summary is not None
        assert summary.lab_result_id == lab_result.id
        assert summary.organization_id == lab_result.organization_id
        assert summary.patient_id == lab_result.patient_id
        assert summary.visit_id == lab_result.visit_id
        assert summary.doctor_id == lab_result.doctor_id
        assert summary.comments == "Sample hemolyzed"
        assert {i.test_name for i in summary.items} == {"CBC", "Lipid Panel"}

    async def test_returns_none_for_an_unknown_lab_order(
        self, service: LabResultQueryService
    ) -> None:
        assert await service.get_lab_result_summary(uuid4()) is None


class TestListLabResultsForPatient:
    async def test_returns_results_scoped_to_the_patient(
        self, service: LabResultQueryService, lab_result_repo: FakeLabResultRepository
    ) -> None:
        patient_id = uuid4()
        await lab_result_repo.add(_make_lab_result(patient_id=patient_id, result_number="RES-A"))
        await lab_result_repo.add(_make_lab_result(result_number="RES-B"))

        summaries = await service.list_lab_results_for_patient(patient_id)

        assert [s.result_number for s in summaries] == ["RES-A"]

    async def test_returns_empty_list_for_a_patient_without_results(
        self, service: LabResultQueryService
    ) -> None:
        assert await service.list_lab_results_for_patient(uuid4()) == []
