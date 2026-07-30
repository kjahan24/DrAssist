"""Unit tests for the `CreateDoctorSchedule` use case, using in-memory
fakes for this module's own repository and the Doctor module's public
port (via `ScheduleConsistencyService`)."""

from datetime import time
from uuid import uuid4

import pytest

from app.modules.schedule.application.dto import CreateDoctorScheduleInput
from app.modules.schedule.application.services.schedule_consistency_service import (
    ScheduleConsistencyService,
)
from app.modules.schedule.application.use_cases.create_doctor_schedule import (
    CreateDoctorSchedule,
)
from app.modules.schedule.domain.enums import Weekday
from app.modules.schedule.domain.events import DoctorScheduleCreated
from app.modules.schedule.domain.exceptions import (
    DoctorNotFoundError,
    DoctorScheduleOverlapError,
)
from tests.unit.modules.schedule.application.fakes import (
    FakeDoctorQueryPort,
    FakeDoctorScheduleRepository,
    FakeUnitOfWork,
    make_doctor_summary,
)


def _make_input(**overrides: object) -> CreateDoctorScheduleInput:
    defaults: dict[str, object] = {
        "doctor_id": uuid4(),
        "weekday": Weekday.MONDAY,
        "start_time": time(9, 0),
        "end_time": time(12, 0),
        "slot_duration_minutes": 30,
    }
    defaults.update(overrides)
    return CreateDoctorScheduleInput(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def schedule_repository() -> FakeDoctorScheduleRepository:
    return FakeDoctorScheduleRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    schedule_repository: FakeDoctorScheduleRepository,
    unit_of_work: FakeUnitOfWork,
    doctor_query_port: FakeDoctorQueryPort,
) -> CreateDoctorSchedule:
    return CreateDoctorSchedule(
        doctor_schedule_repository=schedule_repository,
        consistency_service=ScheduleConsistencyService(doctor_query_port=doctor_query_port),
        unit_of_work=unit_of_work,
    )


class TestCreateDoctorSchedule:
    async def test_creates_schedule_with_derived_organization_id(
        self, schedule_repository: FakeDoctorScheduleRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        organization_id = uuid4()
        doctor_id = uuid4()
        doctor_port = FakeDoctorQueryPort(
            existing_doctors={
                doctor_id: make_doctor_summary(doctor_id=doctor_id, organization_id=organization_id)
            }
        )
        use_case = _use_case(schedule_repository, unit_of_work, doctor_port)

        output = await use_case.execute(_make_input(doctor_id=doctor_id))

        assert output.organization_id == organization_id
        stored = await schedule_repository.get_by_id(output.schedule_id)
        assert stored is not None
        assert stored.doctor_id == doctor_id
        assert unit_of_work.committed is True
        assert any(isinstance(e, DoctorScheduleCreated) for e in unit_of_work.published_events)

    async def test_unknown_doctor_raises(
        self, schedule_repository: FakeDoctorScheduleRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        use_case = _use_case(schedule_repository, unit_of_work, FakeDoctorQueryPort())
        with pytest.raises(DoctorNotFoundError):
            await use_case.execute(_make_input())

    async def test_non_overlapping_schedules_on_the_same_weekday_are_allowed(
        self, schedule_repository: FakeDoctorScheduleRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        doctor_id = uuid4()
        doctor_port = FakeDoctorQueryPort(
            existing_doctors={doctor_id: make_doctor_summary(doctor_id=doctor_id)}
        )
        use_case = _use_case(schedule_repository, unit_of_work, doctor_port)
        await use_case.execute(
            _make_input(doctor_id=doctor_id, start_time=time(9, 0), end_time=time(12, 0))
        )

        output = await use_case.execute(
            _make_input(doctor_id=doctor_id, start_time=time(13, 0), end_time=time(17, 0))
        )

        stored = await schedule_repository.get_by_id(output.schedule_id)
        assert stored is not None

    async def test_overlapping_schedules_on_the_same_weekday_raise(
        self, schedule_repository: FakeDoctorScheduleRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        doctor_id = uuid4()
        doctor_port = FakeDoctorQueryPort(
            existing_doctors={doctor_id: make_doctor_summary(doctor_id=doctor_id)}
        )
        use_case = _use_case(schedule_repository, unit_of_work, doctor_port)
        await use_case.execute(
            _make_input(doctor_id=doctor_id, start_time=time(9, 0), end_time=time(12, 0))
        )

        with pytest.raises(DoctorScheduleOverlapError):
            await use_case.execute(
                _make_input(doctor_id=doctor_id, start_time=time(11, 0), end_time=time(14, 0))
            )

    async def test_overlapping_schedules_on_different_weekdays_are_allowed(
        self, schedule_repository: FakeDoctorScheduleRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        doctor_id = uuid4()
        doctor_port = FakeDoctorQueryPort(
            existing_doctors={doctor_id: make_doctor_summary(doctor_id=doctor_id)}
        )
        use_case = _use_case(schedule_repository, unit_of_work, doctor_port)
        await use_case.execute(
            _make_input(
                doctor_id=doctor_id,
                weekday=Weekday.MONDAY,
                start_time=time(9, 0),
                end_time=time(12, 0),
            )
        )

        output = await use_case.execute(
            _make_input(
                doctor_id=doctor_id,
                weekday=Weekday.TUESDAY,
                start_time=time(9, 0),
                end_time=time(12, 0),
            )
        )

        stored = await schedule_repository.get_by_id(output.schedule_id)
        assert stored is not None

    async def test_overlapping_an_inactive_sibling_is_allowed(
        self, schedule_repository: FakeDoctorScheduleRepository, unit_of_work: FakeUnitOfWork
    ) -> None:
        doctor_id = uuid4()
        doctor_port = FakeDoctorQueryPort(
            existing_doctors={doctor_id: make_doctor_summary(doctor_id=doctor_id)}
        )
        use_case = _use_case(schedule_repository, unit_of_work, doctor_port)
        await use_case.execute(
            _make_input(
                doctor_id=doctor_id,
                start_time=time(9, 0),
                end_time=time(12, 0),
                is_active=False,
            )
        )

        output = await use_case.execute(
            _make_input(doctor_id=doctor_id, start_time=time(10, 0), end_time=time(13, 0))
        )

        stored = await schedule_repository.get_by_id(output.schedule_id)
        assert stored is not None
