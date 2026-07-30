"""Unit tests for the `ActivateDoctorSchedule` use case."""

from datetime import time
from uuid import uuid4

import pytest

from app.modules.schedule.application.dto import ActivateDoctorScheduleInput
from app.modules.schedule.application.use_cases.activate_doctor_schedule import (
    ActivateDoctorSchedule,
)
from app.modules.schedule.domain.entities import DoctorSchedule
from app.modules.schedule.domain.enums import Weekday
from app.modules.schedule.domain.exceptions import (
    DoctorScheduleNotFoundError,
    DoctorScheduleOverlapError,
)
from tests.unit.modules.schedule.application.fakes import (
    FakeDoctorScheduleRepository,
    FakeUnitOfWork,
)


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
) -> ActivateDoctorSchedule:
    return ActivateDoctorSchedule(
        doctor_schedule_repository=schedule_repository, unit_of_work=unit_of_work
    )


class TestActivateDoctorSchedule:
    async def test_activates_an_inactive_schedule(
        self, schedule_repository: FakeDoctorScheduleRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        schedule = _make_schedule(is_active=False)
        await schedule_repository.add(schedule)
        use_case = _use_case(schedule_repository, unit_of_work)

        output = await use_case.execute(ActivateDoctorScheduleInput(schedule_id=schedule.id))

        assert output.is_active is True

    async def test_unknown_schedule_raises(
        self, schedule_repository: FakeDoctorScheduleRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        use_case = _use_case(schedule_repository, unit_of_work)
        with pytest.raises(DoctorScheduleNotFoundError):
            await use_case.execute(ActivateDoctorScheduleInput(schedule_id=uuid4()))

    async def test_activating_into_an_overlapping_active_sibling_raises(
        self, schedule_repository: FakeDoctorScheduleRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        doctor_id = uuid4()
        active_sibling = _make_schedule(
            doctor_id=doctor_id, start_time=time(9, 0), end_time=time(12, 0)
        )
        inactive_target = _make_schedule(
            doctor_id=doctor_id,
            start_time=time(10, 0),
            end_time=time(13, 0),
            is_active=False,
        )
        await schedule_repository.add(active_sibling)
        await schedule_repository.add(inactive_target)
        use_case = _use_case(schedule_repository, unit_of_work)

        with pytest.raises(DoctorScheduleOverlapError):
            await use_case.execute(ActivateDoctorScheduleInput(schedule_id=inactive_target.id))
