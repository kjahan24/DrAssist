"""Unit tests for the `DeactivateDoctorSchedule` use case."""

from datetime import time
from uuid import uuid4

import pytest

from app.modules.schedule.application.dto import DeactivateDoctorScheduleInput
from app.modules.schedule.application.use_cases.deactivate_doctor_schedule import (
    DeactivateDoctorSchedule,
)
from app.modules.schedule.domain.entities import DoctorSchedule
from app.modules.schedule.domain.enums import Weekday
from app.modules.schedule.domain.exceptions import DoctorScheduleNotFoundError
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
) -> DeactivateDoctorSchedule:
    return DeactivateDoctorSchedule(
        doctor_schedule_repository=schedule_repository, unit_of_work=unit_of_work
    )


class TestDeactivateDoctorSchedule:
    async def test_deactivates_an_active_schedule(
        self, schedule_repository: FakeDoctorScheduleRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        schedule = _make_schedule()
        await schedule_repository.add(schedule)
        use_case = _use_case(schedule_repository, unit_of_work)

        output = await use_case.execute(DeactivateDoctorScheduleInput(schedule_id=schedule.id))

        assert output.is_active is False

    async def test_unknown_schedule_raises(
        self, schedule_repository: FakeDoctorScheduleRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        use_case = _use_case(schedule_repository, unit_of_work)
        with pytest.raises(DoctorScheduleNotFoundError):
            await use_case.execute(DeactivateDoctorScheduleInput(schedule_id=uuid4()))
