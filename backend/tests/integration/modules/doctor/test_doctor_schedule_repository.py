"""Integration tests for `SqlAlchemyDoctorScheduleRepository`, including
the FK to `doctors`, against a real PostgreSQL instance."""

from datetime import date, time
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.doctor._helpers import persist_organization, persist_user

from app.modules.doctor.domain.entities import Doctor, DoctorSchedule
from app.modules.doctor.domain.enums import DayOfWeek
from app.modules.doctor.infrastructure.repositories import (
    SqlAlchemyDoctorRepository,
    SqlAlchemyDoctorScheduleRepository,
)


async def _persist_doctor(db_session: AsyncSession) -> Doctor:
    organization = await persist_organization(db_session)
    user = await persist_user(db_session, organization_id=organization.id)
    repo = SqlAlchemyDoctorRepository(db_session)
    doctor = Doctor.create(
        organization_id=organization.id,
        user_id=user.id,
        employee_id="EMP-001",
        joining_date=date(2026, 1, 1),
    )
    await repo.add(doctor)
    await db_session.commit()
    return doctor


class TestDoctorScheduleRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        doctor = await _persist_doctor(db_session)
        repo = SqlAlchemyDoctorScheduleRepository(db_session)

        schedule = DoctorSchedule.create(
            doctor_id=doctor.id,
            day_of_week=DayOfWeek.MONDAY,
            start_time=time(9, 0),
            end_time=time(17, 0),
            break_start=time(12, 0),
            break_end=time(13, 0),
        )
        await repo.add(schedule)
        await db_session.commit()

        reloaded = await repo.get_by_id(schedule.id)
        assert reloaded is not None
        assert reloaded.doctor_id == doctor.id
        assert reloaded.day_of_week is DayOfWeek.MONDAY
        assert reloaded.start_time == time(9, 0)
        assert reloaded.end_time == time(17, 0)
        assert reloaded.break_start == time(12, 0)
        assert reloaded.break_end == time(13, 0)
        assert reloaded.is_available is True

    async def test_list_by_doctor_and_day_filters_correctly(self, db_session: AsyncSession) -> None:
        doctor = await _persist_doctor(db_session)
        repo = SqlAlchemyDoctorScheduleRepository(db_session)

        monday_entry = DoctorSchedule.create(
            doctor_id=doctor.id,
            day_of_week=DayOfWeek.MONDAY,
            start_time=time(9, 0),
            end_time=time(17, 0),
        )
        tuesday_entry = DoctorSchedule.create(
            doctor_id=doctor.id,
            day_of_week=DayOfWeek.TUESDAY,
            start_time=time(9, 0),
            end_time=time(17, 0),
        )
        await repo.add(monday_entry)
        await repo.add(tuesday_entry)
        await db_session.commit()

        monday_only = await repo.list_by_doctor_and_day(doctor.id, DayOfWeek.MONDAY)
        assert [e.id for e in monday_only] == [monday_entry.id]

    async def test_list_by_doctor_returns_all_entries(self, db_session: AsyncSession) -> None:
        doctor = await _persist_doctor(db_session)
        repo = SqlAlchemyDoctorScheduleRepository(db_session)

        morning = DoctorSchedule.create(
            doctor_id=doctor.id,
            day_of_week=DayOfWeek.MONDAY,
            start_time=time(9, 0),
            end_time=time(12, 0),
        )
        afternoon = DoctorSchedule.create(
            doctor_id=doctor.id,
            day_of_week=DayOfWeek.MONDAY,
            start_time=time(13, 0),
            end_time=time(17, 0),
        )
        await repo.add(morning)
        await repo.add(afternoon)
        await db_session.commit()

        entries = await repo.list_by_doctor(doctor.id)
        assert {e.id for e in entries} == {morning.id, afternoon.id}


class TestDoctorScheduleRequiresValidDoctor:
    async def test_nonexistent_doctor_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyDoctorScheduleRepository(db_session)
        schedule = DoctorSchedule.create(
            doctor_id=uuid4(),
            day_of_week=DayOfWeek.MONDAY,
            start_time=time(9, 0),
            end_time=time(17, 0),
        )
        await repo.add(schedule)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
