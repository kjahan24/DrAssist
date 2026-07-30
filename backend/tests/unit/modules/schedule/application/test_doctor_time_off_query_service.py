"""Unit tests for `DoctorTimeOffQueryService` — backs (together with
`DoctorScheduleQueryService`) the module's public `ScheduleQueryPort`
facade."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.schedule.application.services.doctor_time_off_query_service import (
    DoctorTimeOffQueryService,
)
from app.modules.schedule.domain.entities import DoctorTimeOff
from tests.unit.modules.schedule.application.fakes import FakeDoctorTimeOffRepository


def _make_time_off(**overrides: object) -> DoctorTimeOff:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "doctor_id": uuid4(),
        "start_datetime": datetime(2026, 6, 1, tzinfo=UTC),
        "end_datetime": datetime(2026, 6, 5, tzinfo=UTC),
    }
    defaults.update(overrides)
    return DoctorTimeOff.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def repo() -> FakeDoctorTimeOffRepository:
    return FakeDoctorTimeOffRepository()


@pytest.fixture
def service(repo: FakeDoctorTimeOffRepository) -> DoctorTimeOffQueryService:
    return DoctorTimeOffQueryService(doctor_time_off_repository=repo)


class TestDoctorTimeOffExists:
    async def test_true_for_a_known_time_off(
        self, service: DoctorTimeOffQueryService, repo: FakeDoctorTimeOffRepository
    ) -> None:
        time_off = _make_time_off()
        await repo.add(time_off)
        assert await service.doctor_time_off_exists(time_off.id) is True

    async def test_false_for_an_unknown_time_off(self, service: DoctorTimeOffQueryService) -> None:
        assert await service.doctor_time_off_exists(uuid4()) is False


class TestGetDoctorTimeOffSummary:
    async def test_returns_summary_for_a_known_time_off(
        self, service: DoctorTimeOffQueryService, repo: FakeDoctorTimeOffRepository
    ) -> None:
        time_off = _make_time_off(reason="Conference")
        await repo.add(time_off)

        summary = await service.get_doctor_time_off_summary(time_off.id)

        assert summary is not None
        assert summary.time_off_id == time_off.id
        assert summary.organization_id == time_off.organization_id
        assert summary.doctor_id == time_off.doctor_id
        assert summary.reason == "Conference"

    async def test_returns_none_for_an_unknown_time_off(
        self, service: DoctorTimeOffQueryService
    ) -> None:
        assert await service.get_doctor_time_off_summary(uuid4()) is None


class TestListDoctorTimeOff:
    async def test_returns_time_off_ordered_by_start_datetime(
        self, service: DoctorTimeOffQueryService, repo: FakeDoctorTimeOffRepository
    ) -> None:
        doctor_id = uuid4()
        await repo.add(
            _make_time_off(
                doctor_id=doctor_id,
                start_datetime=datetime(2026, 7, 1, tzinfo=UTC),
                end_datetime=datetime(2026, 7, 5, tzinfo=UTC),
            )
        )
        await repo.add(
            _make_time_off(
                doctor_id=doctor_id,
                start_datetime=datetime(2026, 6, 1, tzinfo=UTC),
                end_datetime=datetime(2026, 6, 5, tzinfo=UTC),
            )
        )
        await repo.add(_make_time_off())

        summaries = await service.list_doctor_time_off(doctor_id)

        assert [s.start_datetime for s in summaries] == [
            datetime(2026, 6, 1, tzinfo=UTC),
            datetime(2026, 7, 1, tzinfo=UTC),
        ]

    async def test_returns_empty_list_for_a_doctor_without_time_off(
        self, service: DoctorTimeOffQueryService
    ) -> None:
        assert await service.list_doctor_time_off(uuid4()) == []
