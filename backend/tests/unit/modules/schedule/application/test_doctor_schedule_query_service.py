"""Unit tests for `DoctorScheduleQueryService` — backs (together with
`DoctorTimeOffQueryService`) the module's public `ScheduleQueryPort`
facade."""

from datetime import time
from uuid import uuid4

import pytest

from app.modules.schedule.application.services.doctor_schedule_query_service import (
    DoctorScheduleQueryService,
)
from app.modules.schedule.domain.entities import DoctorSchedule
from app.modules.schedule.domain.enums import Weekday
from tests.unit.modules.schedule.application.fakes import FakeDoctorScheduleRepository


def _make_schedule(**overrides: object) -> DoctorSchedule:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "doctor_id": uuid4(),
        "weekday": Weekday.MONDAY,
        "start_time": time(9, 0),
        "end_time": time(12, 0),
        "slot_duration_minutes": 30,
    }
    defaults.update(overrides)
    return DoctorSchedule.create(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def repo() -> FakeDoctorScheduleRepository:
    return FakeDoctorScheduleRepository()


@pytest.fixture
def service(repo: FakeDoctorScheduleRepository) -> DoctorScheduleQueryService:
    return DoctorScheduleQueryService(doctor_schedule_repository=repo)


class TestDoctorScheduleExists:
    async def test_true_for_a_known_schedule(
        self, service: DoctorScheduleQueryService, repo: FakeDoctorScheduleRepository
    ) -> None:
        schedule = _make_schedule()
        await repo.add(schedule)
        assert await service.doctor_schedule_exists(schedule.id) is True

    async def test_false_for_an_unknown_schedule(self, service: DoctorScheduleQueryService) -> None:
        assert await service.doctor_schedule_exists(uuid4()) is False


class TestGetDoctorScheduleSummary:
    async def test_returns_summary_for_a_known_schedule(
        self, service: DoctorScheduleQueryService, repo: FakeDoctorScheduleRepository
    ) -> None:
        schedule = _make_schedule(slot_duration_minutes=45)
        await repo.add(schedule)

        summary = await service.get_doctor_schedule_summary(schedule.id)

        assert summary is not None
        assert summary.schedule_id == schedule.id
        assert summary.organization_id == schedule.organization_id
        assert summary.doctor_id == schedule.doctor_id
        assert summary.slot_duration_minutes == 45

    async def test_returns_none_for_an_unknown_schedule(
        self, service: DoctorScheduleQueryService
    ) -> None:
        assert await service.get_doctor_schedule_summary(uuid4()) is None


class TestListDoctorSchedules:
    async def test_returns_schedules_ordered_by_weekday_and_start_time(
        self, service: DoctorScheduleQueryService, repo: FakeDoctorScheduleRepository
    ) -> None:
        doctor_id = uuid4()
        await repo.add(
            _make_schedule(doctor_id=doctor_id, weekday=Weekday.TUESDAY, start_time=time(9, 0))
        )
        await repo.add(
            _make_schedule(doctor_id=doctor_id, weekday=Weekday.MONDAY, start_time=time(9, 0))
        )
        await repo.add(_make_schedule())

        summaries = await service.list_doctor_schedules(doctor_id)

        assert [s.weekday for s in summaries] == [Weekday.MONDAY, Weekday.TUESDAY]

    async def test_returns_empty_list_for_a_doctor_without_schedules(
        self, service: DoctorScheduleQueryService
    ) -> None:
        assert await service.list_doctor_schedules(uuid4()) == []


class TestListActiveDoctorSchedulesForWeekday:
    async def test_returns_only_active_entries_for_the_weekday(
        self, service: DoctorScheduleQueryService, repo: FakeDoctorScheduleRepository
    ) -> None:
        doctor_id = uuid4()
        await repo.add(_make_schedule(doctor_id=doctor_id, weekday=Weekday.MONDAY, is_active=True))
        await repo.add(
            _make_schedule(
                doctor_id=doctor_id,
                weekday=Weekday.MONDAY,
                start_time=time(13, 0),
                end_time=time(17, 0),
                is_active=False,
            )
        )
        await repo.add(_make_schedule(doctor_id=doctor_id, weekday=Weekday.TUESDAY))

        summaries = await service.list_active_doctor_schedules_for_weekday(
            doctor_id, Weekday.MONDAY
        )

        assert len(summaries) == 1
        assert summaries[0].is_active is True

    async def test_returns_empty_list_when_none_match(
        self, service: DoctorScheduleQueryService
    ) -> None:
        assert await service.list_active_doctor_schedules_for_weekday(uuid4(), Weekday.SUNDAY) == []
