"""Unit tests for `PatientHistoryQueryService` — backs the module's
public `PatientHistoryQueryPort` facade."""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.patient_history.application.services.patient_history_query_service import (
    PatientHistoryQueryService,
)
from app.modules.patient_history.domain.entities import PatientHistory
from app.modules.patient_history.domain.enums import HistoryType, ReferenceType
from tests.unit.modules.patient_history.application.fakes import FakePatientHistoryRepository


def _make_history(**overrides: object) -> PatientHistory:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "visit_id": uuid4(),
        "doctor_review_id": uuid4(),
        "history_type": HistoryType.DIAGNOSIS,
        "reference_type": ReferenceType.ICD10,
        "reference_id": uuid4(),
        "encounter_date": date(2026, 1, 1),
        "summary": "Community-acquired pneumonia, J18.9",
    }
    defaults.update(overrides)
    return PatientHistory.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def repo() -> FakePatientHistoryRepository:
    return FakePatientHistoryRepository()


@pytest.fixture
def service(repo: FakePatientHistoryRepository) -> PatientHistoryQueryService:
    return PatientHistoryQueryService(patient_history_repository=repo)


class TestPatientHistoryExists:
    async def test_true_for_a_known_record(
        self, service: PatientHistoryQueryService, repo: FakePatientHistoryRepository
    ) -> None:
        history = _make_history()
        await repo.add(history)
        assert await service.patient_history_exists(history.id) is True

    async def test_false_for_an_unknown_record(self, service: PatientHistoryQueryService) -> None:
        assert await service.patient_history_exists(uuid4()) is False


class TestGetPatientHistorySummary:
    async def test_returns_summary_for_a_known_record(
        self, service: PatientHistoryQueryService, repo: FakePatientHistoryRepository
    ) -> None:
        history = _make_history(summary="Confirmed pneumonia")
        await repo.add(history)

        summary = await service.get_patient_history_summary(history.id)

        assert summary is not None
        assert summary.patient_history_id == history.id
        assert summary.organization_id == history.organization_id
        assert summary.patient_id == history.patient_id
        assert summary.visit_id == history.visit_id
        assert summary.doctor_review_id == history.doctor_review_id
        assert summary.summary == "Confirmed pneumonia"
        assert summary.created_from_review is True

    async def test_returns_none_for_an_unknown_record(
        self, service: PatientHistoryQueryService
    ) -> None:
        assert await service.get_patient_history_summary(uuid4()) is None


class TestGetByReference:
    async def test_returns_the_matching_record(
        self, service: PatientHistoryQueryService, repo: FakePatientHistoryRepository
    ) -> None:
        reference_id = uuid4()
        history = _make_history(
            reference_type=ReferenceType.PRESCRIPTION, reference_id=reference_id
        )
        await repo.add(history)

        summary = await service.get_by_reference(ReferenceType.PRESCRIPTION, reference_id)

        assert summary is not None
        assert summary.patient_history_id == history.id

    async def test_returns_none_for_an_unmatched_reference(
        self, service: PatientHistoryQueryService
    ) -> None:
        assert await service.get_by_reference(ReferenceType.PRESCRIPTION, uuid4()) is None


class TestListPatientHistoryForPatient:
    async def test_returns_history_scoped_to_the_patient_ordered_by_encounter_date(
        self, service: PatientHistoryQueryService, repo: FakePatientHistoryRepository
    ) -> None:
        patient_id = uuid4()
        await repo.add(
            _make_history(patient_id=patient_id, encounter_date=date(2026, 2, 1), summary="Second")
        )
        await repo.add(
            _make_history(patient_id=patient_id, encounter_date=date(2026, 1, 1), summary="First")
        )
        await repo.add(_make_history(summary="Other patient"))

        summaries = await service.list_patient_history_for_patient(patient_id)

        assert [s.summary for s in summaries] == ["First", "Second"]

    async def test_returns_empty_list_for_a_patient_without_history(
        self, service: PatientHistoryQueryService
    ) -> None:
        assert await service.list_patient_history_for_patient(uuid4()) == []


class TestListPatientHistoryForVisit:
    async def test_returns_history_scoped_to_the_visit(
        self, service: PatientHistoryQueryService, repo: FakePatientHistoryRepository
    ) -> None:
        visit_id = uuid4()
        await repo.add(_make_history(visit_id=visit_id, summary="For our visit"))
        await repo.add(_make_history(summary="For other visit"))

        summaries = await service.list_patient_history_for_visit(visit_id)

        assert [s.summary for s in summaries] == ["For our visit"]

    async def test_returns_empty_list_for_a_visit_without_history(
        self, service: PatientHistoryQueryService
    ) -> None:
        assert await service.list_patient_history_for_visit(uuid4()) == []
