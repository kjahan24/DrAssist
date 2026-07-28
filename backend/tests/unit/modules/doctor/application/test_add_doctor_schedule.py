"""Unit tests for the `AddDoctorSchedule` use case, including the
"schedule cannot overlap for the same doctor" invariant."""

from datetime import date, time
from uuid import uuid4

import pytest

from app.modules.doctor.application.dto import AddDoctorScheduleInput
from app.modules.doctor.application.use_cases.add_doctor_schedule import AddDoctorSchedule
from app.modules.doctor.domain.entities import Doctor
from app.modules.doctor.domain.enums import DayOfWeek
from app.modules.doctor.domain.events import DoctorScheduleAdded
from app.modules.doctor.domain.exceptions import DoctorNotFoundError, ScheduleOverlapError
from tests.unit.modules.doctor.application.fakes import (
    FakeDoctorRepository,
    FakeDoctorScheduleRepository,
    FakeUnitOfWork,
)


def _make_doctor() -> Doctor:
    return Doctor.create(
        organization_id=uuid4(),
        user_id=uuid4(),
        employee_id="EMP-001",
        joining_date=date(2026, 1, 1),
    )


@pytest.fixture
def doctor_schedule_repository() -> FakeDoctorScheduleRepository:
    return FakeDoctorScheduleRepository()


@pytest.fixture
def doctor_repository() -> FakeDoctorRepository:
    return FakeDoctorRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def use_case(
    doctor_schedule_repository: FakeDoctorScheduleRepository,
    doctor_repository: FakeDoctorRepository,
    unit_of_work: FakeUnitOfWork,
) -> AddDoctorSchedule:
    return AddDoctorSchedule(
        doctor_schedule_repository=doctor_schedule_repository,
        doctor_repository=doctor_repository,
        unit_of_work=unit_of_work,
    )


class TestAddDoctorSchedule:
    async def test_adds_schedule_for_existing_doctor(
        self,
        use_case: AddDoctorSchedule,
        doctor_repository: FakeDoctorRepository,
        doctor_schedule_repository: FakeDoctorScheduleRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        doctor = _make_doctor()
        await doctor_repository.add(doctor)

        output = await use_case.execute(
            AddDoctorScheduleInput(
                doctor_id=doctor.id,
                day_of_week=DayOfWeek.MONDAY,
                start_time=time(9, 0),
                end_time=time(17, 0),
            )
        )

        stored = await doctor_schedule_repository.get_by_id(output.schedule_id)
        assert stored is not None
        assert unit_of_work.committed is True
        assert any(isinstance(e, DoctorScheduleAdded) for e in unit_of_work.published_events)

    async def test_unknown_doctor_raises(self, use_case: AddDoctorSchedule) -> None:
        with pytest.raises(DoctorNotFoundError):
            await use_case.execute(
                AddDoctorScheduleInput(
                    doctor_id=uuid4(),
                    day_of_week=DayOfWeek.MONDAY,
                    start_time=time(9, 0),
                    end_time=time(17, 0),
                )
            )

    async def test_overlapping_entry_on_the_same_day_is_rejected(
        self, use_case: AddDoctorSchedule, doctor_repository: FakeDoctorRepository
    ) -> None:
        doctor = _make_doctor()
        await doctor_repository.add(doctor)

        await use_case.execute(
            AddDoctorScheduleInput(
                doctor_id=doctor.id,
                day_of_week=DayOfWeek.MONDAY,
                start_time=time(9, 0),
                end_time=time(13, 0),
            )
        )

        with pytest.raises(ScheduleOverlapError):
            await use_case.execute(
                AddDoctorScheduleInput(
                    doctor_id=doctor.id,
                    day_of_week=DayOfWeek.MONDAY,
                    start_time=time(12, 0),
                    end_time=time(17, 0),
                )
            )

    async def test_non_overlapping_entries_on_the_same_day_are_both_accepted(
        self,
        use_case: AddDoctorSchedule,
        doctor_repository: FakeDoctorRepository,
        doctor_schedule_repository: FakeDoctorScheduleRepository,
    ) -> None:
        doctor = _make_doctor()
        await doctor_repository.add(doctor)

        await use_case.execute(
            AddDoctorScheduleInput(
                doctor_id=doctor.id,
                day_of_week=DayOfWeek.MONDAY,
                start_time=time(9, 0),
                end_time=time(12, 0),
            )
        )
        await use_case.execute(
            AddDoctorScheduleInput(
                doctor_id=doctor.id,
                day_of_week=DayOfWeek.MONDAY,
                start_time=time(13, 0),
                end_time=time(17, 0),
            )
        )

        entries = await doctor_schedule_repository.list_by_doctor(doctor.id)
        assert len(entries) == 2

    async def test_overlapping_entry_on_a_different_day_is_accepted(
        self, use_case: AddDoctorSchedule, doctor_repository: FakeDoctorRepository
    ) -> None:
        doctor = _make_doctor()
        await doctor_repository.add(doctor)

        await use_case.execute(
            AddDoctorScheduleInput(
                doctor_id=doctor.id,
                day_of_week=DayOfWeek.MONDAY,
                start_time=time(9, 0),
                end_time=time(17, 0),
            )
        )

        output = await use_case.execute(
            AddDoctorScheduleInput(
                doctor_id=doctor.id,
                day_of_week=DayOfWeek.TUESDAY,
                start_time=time(9, 0),
                end_time=time(17, 0),
            )
        )
        assert output.day_of_week is DayOfWeek.TUESDAY
