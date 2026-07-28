"""Unit tests for `PatientVisitQueryService` — backs the module's public
`VisitQueryPort` facade."""

from datetime import date, datetime
from uuid import uuid4

import pytest

from app.modules.visit.application.services.patient_visit_query_service import (
    PatientVisitQueryService,
)
from app.modules.visit.domain.entities import PatientVisit
from app.modules.visit.domain.enums import VisitType
from tests.unit.modules.visit.application.fakes import FakePatientVisitRepository


def _make_visit(**overrides: object) -> PatientVisit:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "doctor_id": uuid4(),
        "visit_number": "V-0001",
        "visit_type": VisitType.CONSULTATION,
        "visit_date": date(2026, 1, 1),
    }
    defaults.update(overrides)
    return PatientVisit.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def visit_repo() -> FakePatientVisitRepository:
    return FakePatientVisitRepository()


@pytest.fixture
def service(visit_repo: FakePatientVisitRepository) -> PatientVisitQueryService:
    return PatientVisitQueryService(patient_visit_repository=visit_repo)


class TestVisitExists:
    async def test_true_for_a_known_visit(
        self, service: PatientVisitQueryService, visit_repo: FakePatientVisitRepository
    ) -> None:
        visit = _make_visit()
        await visit_repo.add(visit)
        assert await service.visit_exists(visit.id) is True

    async def test_false_for_an_unknown_visit(self, service: PatientVisitQueryService) -> None:
        assert await service.visit_exists(uuid4()) is False


class TestIsActive:
    async def test_true_while_scheduled(
        self, service: PatientVisitQueryService, visit_repo: FakePatientVisitRepository
    ) -> None:
        visit = _make_visit()
        await visit_repo.add(visit)
        assert await service.is_active(visit.id) is True

    async def test_false_once_cancelled(
        self, service: PatientVisitQueryService, visit_repo: FakePatientVisitRepository
    ) -> None:
        visit = _make_visit()
        visit.cancel()
        await visit_repo.add(visit)
        assert await service.is_active(visit.id) is False

    async def test_false_once_completed(
        self, service: PatientVisitQueryService, visit_repo: FakePatientVisitRepository
    ) -> None:
        visit = _make_visit()
        visit.start_consultation(consultation_start_time=datetime(2026, 1, 1, 9, 0))
        visit.complete(consultation_end_time=datetime(2026, 1, 1, 9, 20))
        await visit_repo.add(visit)
        assert await service.is_active(visit.id) is False

    async def test_false_for_an_unknown_visit(self, service: PatientVisitQueryService) -> None:
        assert await service.is_active(uuid4()) is False


class TestGetVisitSummary:
    async def test_returns_summary_for_known_visit(
        self, service: PatientVisitQueryService, visit_repo: FakePatientVisitRepository
    ) -> None:
        visit = _make_visit(visit_number="V-42")
        await visit_repo.add(visit)

        summary = await service.get_visit_summary(visit.id)

        assert summary is not None
        assert summary.visit_number == "V-42"
        assert summary.organization_id == visit.organization_id
        assert summary.patient_id == visit.patient_id
        assert summary.doctor_id == visit.doctor_id

    async def test_returns_none_for_unknown_visit(self, service: PatientVisitQueryService) -> None:
        assert await service.get_visit_summary(uuid4()) is None
