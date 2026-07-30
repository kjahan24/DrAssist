"""Integration tests for `SqlAlchemyDoctorTimeOffRepository`, including
the FKs to `organizations`/`doctors` and the `end_datetime >
start_datetime` `CHECK` constraint, against a real PostgreSQL instance.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.schedule._helpers import persist_full_chain

from app.modules.schedule.domain.entities import DoctorTimeOff
from app.modules.schedule.infrastructure.models import DoctorTimeOffModel
from app.modules.schedule.infrastructure.repositories import SqlAlchemyDoctorTimeOffRepository


class TestDoctorTimeOffRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, doctor = await persist_full_chain(db_session)
        repo = SqlAlchemyDoctorTimeOffRepository(db_session)

        time_off = DoctorTimeOff.create(
            organization_id=organization.id,
            doctor_id=doctor.id,
            start_datetime=datetime(2026, 6, 1, tzinfo=UTC),
            end_datetime=datetime(2026, 6, 5, tzinfo=UTC),
            reason="Annual leave",
        )
        await repo.add(time_off)
        await db_session.commit()

        reloaded = await repo.get_by_id(time_off.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.doctor_id == doctor.id
        assert reloaded.start_datetime == datetime(2026, 6, 1, tzinfo=UTC)
        assert reloaded.end_datetime == datetime(2026, 6, 5, tzinfo=UTC)
        assert reloaded.reason == "Annual leave"

    async def test_update_persists(self, db_session: AsyncSession) -> None:
        organization, doctor = await persist_full_chain(db_session)
        repo = SqlAlchemyDoctorTimeOffRepository(db_session)

        time_off = DoctorTimeOff.create(
            organization_id=organization.id,
            doctor_id=doctor.id,
            start_datetime=datetime(2026, 6, 1, tzinfo=UTC),
            end_datetime=datetime(2026, 6, 5, tzinfo=UTC),
        )
        await repo.add(time_off)
        await db_session.commit()

        time_off.update_details(reason="Updated reason")
        await repo.add(time_off)
        await db_session.commit()

        reloaded = await repo.get_by_id(time_off.id)
        assert reloaded is not None
        assert reloaded.reason == "Updated reason"


class TestListByDoctor:
    async def test_returns_time_off_ordered_by_start_datetime(
        self, db_session: AsyncSession
    ) -> None:
        organization, doctor = await persist_full_chain(db_session)
        repo = SqlAlchemyDoctorTimeOffRepository(db_session)

        await repo.add(
            DoctorTimeOff.create(
                organization_id=organization.id,
                doctor_id=doctor.id,
                start_datetime=datetime(2026, 7, 1, tzinfo=UTC),
                end_datetime=datetime(2026, 7, 5, tzinfo=UTC),
            )
        )
        await repo.add(
            DoctorTimeOff.create(
                organization_id=organization.id,
                doctor_id=doctor.id,
                start_datetime=datetime(2026, 6, 1, tzinfo=UTC),
                end_datetime=datetime(2026, 6, 5, tzinfo=UTC),
            )
        )
        await db_session.commit()

        time_off_periods = await repo.list_by_doctor(doctor.id)
        assert [t.start_datetime for t in time_off_periods] == [
            datetime(2026, 6, 1, tzinfo=UTC),
            datetime(2026, 7, 1, tzinfo=UTC),
        ]

    async def test_returns_empty_list_for_a_doctor_without_time_off(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyDoctorTimeOffRepository(db_session)
        assert await repo.list_by_doctor(uuid4()) == []


class TestDoctorTimeOffRequiresValidReferences:
    async def test_nonexistent_organization_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        _organization, doctor = await persist_full_chain(db_session)
        repo = SqlAlchemyDoctorTimeOffRepository(db_session)

        time_off = DoctorTimeOff.create(
            organization_id=uuid4(),
            doctor_id=doctor.id,
            start_datetime=datetime(2026, 6, 1, tzinfo=UTC),
            end_datetime=datetime(2026, 6, 5, tzinfo=UTC),
        )
        await repo.add(time_off)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_doctor_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _doctor = await persist_full_chain(db_session)
        repo = SqlAlchemyDoctorTimeOffRepository(db_session)

        time_off = DoctorTimeOff.create(
            organization_id=organization.id,
            doctor_id=uuid4(),
            start_datetime=datetime(2026, 6, 1, tzinfo=UTC),
            end_datetime=datetime(2026, 6, 5, tzinfo=UTC),
        )
        await repo.add(time_off)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestCheckConstraints:
    """`DoctorTimeOff.__post_init__` already prevents `end_datetime <=
    start_datetime` from ever existing via the domain layer — this test
    targets the DB `CHECK` constraint directly (bypassing the domain
    entity, the way a direct SQL edit would) to prove the
    defense-in-depth layer actually works.
    """

    async def test_end_not_after_start_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, doctor = await persist_full_chain(db_session)

        model = DoctorTimeOffModel(
            organization_id=organization.id,
            doctor_id=doctor.id,
            start_datetime=datetime(2026, 6, 5, tzinfo=UTC),
            end_datetime=datetime(2026, 6, 1, tzinfo=UTC),
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
