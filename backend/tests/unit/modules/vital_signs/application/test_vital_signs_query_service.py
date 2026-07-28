"""Unit tests for `VisitVitalSignsQueryService` — backs the module's
public `VitalSignsQueryPort` facade."""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.modules.vital_signs.application.services.vital_signs_query_service import (
    VisitVitalSignsQueryService,
)
from app.modules.vital_signs.domain.entities import VisitVitalSigns
from app.modules.vital_signs.domain.value_objects import BloodPressure
from tests.unit.modules.vital_signs.application.fakes import FakeVisitVitalSignsRepository


def _make_vital_signs(**overrides: object) -> VisitVitalSigns:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "visit_id": uuid4(),
        "temperature_c": Decimal("37.0"),
        "pulse_bpm": 72,
        "respiratory_rate": 16,
        "blood_pressure": BloodPressure(systolic=120, diastolic=80),
        "spo2": 98,
        "recorded_at": datetime(2026, 1, 1, 9, 0),
    }
    defaults.update(overrides)
    return VisitVitalSigns.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def vital_signs_repo() -> FakeVisitVitalSignsRepository:
    return FakeVisitVitalSignsRepository()


@pytest.fixture
def service(vital_signs_repo: FakeVisitVitalSignsRepository) -> VisitVitalSignsQueryService:
    return VisitVitalSignsQueryService(vital_signs_repository=vital_signs_repo)


class TestVitalSignsExistForVisit:
    async def test_true_for_a_visit_with_recorded_vital_signs(
        self,
        service: VisitVitalSignsQueryService,
        vital_signs_repo: FakeVisitVitalSignsRepository,
    ) -> None:
        vital_signs = _make_vital_signs()
        await vital_signs_repo.add(vital_signs)
        assert await service.vital_signs_exist_for_visit(vital_signs.visit_id) is True

    async def test_false_for_a_visit_without_vital_signs(
        self, service: VisitVitalSignsQueryService
    ) -> None:
        assert await service.vital_signs_exist_for_visit(uuid4()) is False


class TestGetVitalSignsSummaryForVisit:
    async def test_returns_summary_for_a_recorded_visit(
        self,
        service: VisitVitalSignsQueryService,
        vital_signs_repo: FakeVisitVitalSignsRepository,
    ) -> None:
        vital_signs = _make_vital_signs(height_cm=Decimal("170"), weight_kg=Decimal("70"))
        await vital_signs_repo.add(vital_signs)

        summary = await service.get_vital_signs_summary_for_visit(vital_signs.visit_id)

        assert summary is not None
        assert summary.visit_id == vital_signs.visit_id
        assert summary.organization_id == vital_signs.organization_id
        assert summary.bmi == Decimal("24.2")

    async def test_returns_none_for_a_visit_without_vital_signs(
        self, service: VisitVitalSignsQueryService
    ) -> None:
        assert await service.get_vital_signs_summary_for_visit(uuid4()) is None
