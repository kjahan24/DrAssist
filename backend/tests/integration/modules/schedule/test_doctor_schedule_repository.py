"""Integration tests for `SqlAlchemyDoctorScheduleRepository`, including
the FKs to `organizations`/`doctors`, the `end_time > start_time` and
`slot_duration_minutes > 0` `CHECK` constraints, against a real
PostgreSQL instance.
"""

from datetime import time
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.schedule._helpers import persist_full_chain

from app.modules.schedule.domain.entities import DoctorSchedule
from app.modules.schedule.domain.enums import Weekday
from app.modules.schedule.infrastructure.models import DoctorScheduleModel
from app.modules.schedule.infrastructure.repositories import SqlAlchemyDoctorScheduleRepository


class TestDoctorScheduleRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, doctor = await persist_full_chain(db_session)
        repo = SqlAlchemyDoctorScheduleRepository(db_session)

        schedule = DoctorSchedule.create(
            organization_id=organization.id,
            doctor_id=doctor.id,
            weekday=Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(17, 0),
            slot_duration_minutes=30,
        )
        await repo.add(schedule)
        await db_session.commit()

        reloaded = await repo.get_by_id(schedule.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.doctor_id == doctor.id
        assert reloaded.weekday is Weekday.MONDAY
        assert reloaded.start_time == time(9, 0)
        assert reloaded.end_time == time(17, 0)
        assert reloaded.slot_duration_minutes == 30
        assert reloaded.is_active is True

    async def test_deactivate_then_activate_persists(self, db_session: AsyncSession) -> None:
        organization, doctor = await persist_full_chain(db_session)
        repo = SqlAlchemyDoctorScheduleRepository(db_session)

        schedule = DoctorSchedule.create(
            organization_id=organization.id,
            doctor_id=doctor.id,
            weekday=Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(17, 0),
            slot_duration_minutes=30,
        )
        await repo.add(schedule)
        await db_session.commit()

        schedule.deactivate()
        await repo.add(schedule)
        await db_session.commit()

        deactivated = await repo.get_by_id(schedule.id)
        assert deactivated is not None
        assert deactivated.is_active is False

        deactivated.activate()
        await repo.add(deactivated)
        await db_session.commit()

        reactivated = await repo.get_by_id(schedule.id)
        assert reactivated is not None
        assert reactivated.is_active is True


class TestListByDoctor:
    async def test_returns_schedules_ordered_by_weekday_and_start_time(
        self, db_session: AsyncSession
    ) -> None:
        organization, doctor = await persist_full_chain(db_session)
        repo = SqlAlchemyDoctorScheduleRepository(db_session)

        await repo.add(
            DoctorSchedule.create(
                organization_id=organization.id,
                doctor_id=doctor.id,
                weekday=Weekday.TUESDAY,
                start_time=time(9, 0),
                end_time=time(12, 0),
                slot_duration_minutes=30,
            )
        )
        await repo.add(
            DoctorSchedule.create(
                organization_id=organization.id,
                doctor_id=doctor.id,
                weekday=Weekday.MONDAY,
                start_time=time(9, 0),
                end_time=time(12, 0),
                slot_duration_minutes=30,
            )
        )
        await db_session.commit()

        schedules = await repo.list_by_doctor(doctor.id)
        assert [s.weekday for s in schedules] == [Weekday.MONDAY, Weekday.TUESDAY]

    async def test_returns_empty_list_for_a_doctor_without_schedules(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyDoctorScheduleRepository(db_session)
        assert await repo.list_by_doctor(uuid4()) == []


class TestListActiveByDoctorAndWeekday:
    async def test_returns_only_active_entries_for_the_weekday(
        self, db_session: AsyncSession
    ) -> None:
        organization, doctor = await persist_full_chain(db_session)
        repo = SqlAlchemyDoctorScheduleRepository(db_session)

        active = DoctorSchedule.create(
            organization_id=organization.id,
            doctor_id=doctor.id,
            weekday=Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(12, 0),
            slot_duration_minutes=30,
        )
        inactive = DoctorSchedule.create(
            organization_id=organization.id,
            doctor_id=doctor.id,
            weekday=Weekday.MONDAY,
            start_time=time(13, 0),
            end_time=time(17, 0),
            slot_duration_minutes=30,
            is_active=False,
        )
        other_weekday = DoctorSchedule.create(
            organization_id=organization.id,
            doctor_id=doctor.id,
            weekday=Weekday.TUESDAY,
            start_time=time(9, 0),
            end_time=time(12, 0),
            slot_duration_minutes=30,
        )
        await repo.add(active)
        await repo.add(inactive)
        await repo.add(other_weekday)
        await db_session.commit()

        found = await repo.list_active_by_doctor_and_weekday(doctor.id, Weekday.MONDAY)
        assert [s.id for s in found] == [active.id]

    async def test_returns_empty_list_when_none_match(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyDoctorScheduleRepository(db_session)
        assert await repo.list_active_by_doctor_and_weekday(uuid4(), Weekday.SUNDAY) == []


class TestDoctorScheduleRequiresValidReferences:
    async def test_nonexistent_organization_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        _organization, doctor = await persist_full_chain(db_session)
        repo = SqlAlchemyDoctorScheduleRepository(db_session)

        schedule = DoctorSchedule.create(
            organization_id=uuid4(),
            doctor_id=doctor.id,
            weekday=Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(12, 0),
            slot_duration_minutes=30,
        )
        await repo.add(schedule)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_doctor_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _doctor = await persist_full_chain(db_session)
        repo = SqlAlchemyDoctorScheduleRepository(db_session)

        schedule = DoctorSchedule.create(
            organization_id=organization.id,
            doctor_id=uuid4(),
            weekday=Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(12, 0),
            slot_duration_minutes=30,
        )
        await repo.add(schedule)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestCheckConstraints:
    """`DoctorSchedule.__post_init__` already prevents `end_time <=
    start_time`/`slot_duration_minutes <= 0` from ever existing via the
    domain layer — these tests target the DB `CHECK` constraints
    directly (bypassing the domain entity, the way a direct SQL edit
    would) to prove the defense-in-depth layer actually works, the same
    pattern `tests.integration.modules.differential_diagnosis
    .test_differential_diagnosis_repository.TestCheckConstraints`
    already established.
    """

    async def test_end_time_not_after_start_time_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, doctor = await persist_full_chain(db_session)

        model = DoctorScheduleModel(
            organization_id=organization.id,
            doctor_id=doctor.id,
            weekday=Weekday.MONDAY,
            start_time=time(12, 0),
            end_time=time(9, 0),
            slot_duration_minutes=30,
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_zero_slot_duration_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, doctor = await persist_full_chain(db_session)

        model = DoctorScheduleModel(
            organization_id=organization.id,
            doctor_id=doctor.id,
            weekday=Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(12, 0),
            slot_duration_minutes=0,
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
