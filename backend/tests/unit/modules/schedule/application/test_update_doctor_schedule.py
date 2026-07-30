"""Unit tests for the `UpdateDoctorSchedule` use case."""

from datetime import time
from uuid import uuid4

import pytest

from app.modules.schedule.application.dto import UpdateDoctorScheduleInput
from app.modules.schedule.application.use_cases.update_doctor_schedule import (
    UpdateDoctorSchedule,
)
from app.modules.schedule.domain.entities import DoctorSchedule
from app.modules.schedule.domain.enums import Weekday
from app.modules.schedule.domain.events import DoctorScheduleUpdated
from app.modules.schedule.domain.exceptions import (
    DoctorScheduleNotFoundError,
    DoctorScheduleOverlapError,
    InvalidScheduleTimeRangeError,
)
from tests.unit.modules.schedule.application.fakes import (
    FakeDoctorScheduleRepository,
    FakeUnitOfWork,
)


def _make_input(**overrides: object) -> UpdateDoctorScheduleInput:
    defaults: dict[str, object] = {"schedule_id": uuid4()}
    defaults.update(overrides)
    return UpdateDoctorScheduleInput(**defaults)  # type: ignore[arg-type]


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
def schedule_repository() -> FakeDoctorScheduleRepository:
    return FakeDoctorScheduleRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    schedule_repository: FakeDoctorScheduleRepository, unit_of_work: FakeUnitOfWork
) -> UpdateDoctorSchedule:
    return UpdateDoctorSchedule(
        doctor_schedule_repository=schedule_repository, unit_of_work=unit_of_work
    )


class TestUpdateDoctorSchedule:
    async def test_updates_fields(
        self, schedule_repository: FakeDoctorScheduleRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        schedule = _make_schedule()
        await schedule_repository.add(schedule)
        use_case = _use_case(schedule_repository, unit_of_work)

        await use_case.execute(_make_input(schedule_id=schedule.id, slot_duration_minutes=15))

        stored = await schedule_repository.get_by_id(schedule.id)
        assert stored is not None
        assert stored.slot_duration_minutes == 15
        assert unit_of_work.committed is True
        assert any(isinstance(e, DoctorScheduleUpdated) for e in unit_of_work.published_events)

    async def test_unknown_schedule_raises(
        self, schedule_repository: FakeDoctorScheduleRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        use_case = _use_case(schedule_repository, unit_of_work)
        with pytest.raises(DoctorScheduleNotFoundError):
            await use_case.execute(_make_input(schedule_id=uuid4()))

    async def test_invalid_time_range_raises(
        self, schedule_repository: FakeDoctorScheduleRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        schedule = _make_schedule(start_time=time(9, 0), end_time=time(12, 0))
        await schedule_repository.add(schedule)
        use_case = _use_case(schedule_repository, unit_of_work)

        with pytest.raises(InvalidScheduleTimeRangeError):
            await use_case.execute(_make_input(schedule_id=schedule.id, start_time=time(13, 0)))

    async def test_rescheduling_into_an_active_siblings_range_raises(
        self, schedule_repository: FakeDoctorScheduleRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        doctor_id = uuid4()
        sibling = _make_schedule(doctor_id=doctor_id, start_time=time(13, 0), end_time=time(17, 0))
        target = _make_schedule(doctor_id=doctor_id, start_time=time(9, 0), end_time=time(12, 0))
        await schedule_repository.add(sibling)
        await schedule_repository.add(target)
        use_case = _use_case(schedule_repository, unit_of_work)

        with pytest.raises(DoctorScheduleOverlapError):
            await use_case.execute(_make_input(schedule_id=target.id, end_time=time(14, 0)))

    async def test_rescheduling_an_inactive_schedule_skips_overlap_check(
        self, schedule_repository: FakeDoctorScheduleRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        doctor_id = uuid4()
        sibling = _make_schedule(doctor_id=doctor_id, start_time=time(13, 0), end_time=time(17, 0))
        target = _make_schedule(
            doctor_id=doctor_id,
            start_time=time(9, 0),
            end_time=time(12, 0),
            is_active=False,
        )
        await schedule_repository.add(sibling)
        await schedule_repository.add(target)
        use_case = _use_case(schedule_repository, unit_of_work)

        await use_case.execute(_make_input(schedule_id=target.id, end_time=time(14, 0)))

        stored = await schedule_repository.get_by_id(target.id)
        assert stored is not None
        assert stored.end_time == time(14, 0)
