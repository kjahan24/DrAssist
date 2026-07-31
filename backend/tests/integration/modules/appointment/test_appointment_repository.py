"""Integration tests for `SqlAlchemyAppointmentRepository`, including the
FKs to `organizations`/`patients`/`doctors`/`users`/`patient_visits`, the
"appointment number must be globally unique" partial unique index, and
the `end_time > start_time` `CHECK` constraint, against a real
PostgreSQL instance.
"""

from datetime import date, time
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.appointment._helpers import (
    persist_full_chain,
    persist_user,
    persist_visit,
)

from app.modules.appointment.domain.entities import Appointment
from app.modules.appointment.domain.enums import AppointmentStatus, AppointmentType
from app.modules.appointment.infrastructure.models import AppointmentModel
from app.modules.appointment.infrastructure.repositories import SqlAlchemyAppointmentRepository


class TestAppointmentRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, patient, doctor = await persist_full_chain(db_session)
        repo = SqlAlchemyAppointmentRepository(db_session)

        appointment = Appointment.create(
            organization_id=organization.id,
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_number=f"APT-{uuid4().hex[:12].upper()}",
            appointment_date=date(2026, 3, 1),
            start_time=time(9, 0),
            end_time=time(9, 30),
            appointment_type=AppointmentType.CONSULTATION,
            reason_for_visit="Annual check-up",
            notes="Bring prior lab results",
        )
        await repo.add(appointment)
        await db_session.commit()

        reloaded = await repo.get_by_id(appointment.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.patient_id == patient.id
        assert reloaded.doctor_id == doctor.id
        assert reloaded.appointment_date == date(2026, 3, 1)
        assert reloaded.start_time == time(9, 0)
        assert reloaded.end_time == time(9, 30)
        assert reloaded.appointment_type is AppointmentType.CONSULTATION
        assert reloaded.status is AppointmentStatus.SCHEDULED
        assert reloaded.reason_for_visit == "Annual check-up"
        assert reloaded.notes == "Bring prior lab results"
        assert reloaded.booked_by_user_id is None
        assert reloaded.visit_id is None

    async def test_save_with_booked_by_user_preserves_the_link(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor = await persist_full_chain(db_session)
        booking_user = await persist_user(db_session, organization_id=organization.id)
        repo = SqlAlchemyAppointmentRepository(db_session)

        appointment = Appointment.create(
            organization_id=organization.id,
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_number=f"APT-{uuid4().hex[:12].upper()}",
            appointment_date=date(2026, 3, 1),
            start_time=time(9, 0),
            end_time=time(9, 30),
            appointment_type=AppointmentType.CONSULTATION,
            booked_by_user_id=booking_user.id,
        )
        await repo.add(appointment)
        await db_session.commit()

        reloaded = await repo.get_by_id(appointment.id)
        assert reloaded is not None
        assert reloaded.booked_by_user_id == booking_user.id

    async def test_full_workflow_persists(self, db_session: AsyncSession) -> None:
        organization, patient, doctor = await persist_full_chain(db_session)
        visit = await persist_visit(
            db_session, organization_id=organization.id, patient_id=patient.id, doctor_id=doctor.id
        )
        repo = SqlAlchemyAppointmentRepository(db_session)

        appointment = Appointment.create(
            organization_id=organization.id,
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_number=f"APT-{uuid4().hex[:12].upper()}",
            appointment_date=date(2026, 3, 1),
            start_time=time(9, 0),
            end_time=time(9, 30),
            appointment_type=AppointmentType.CONSULTATION,
        )
        await repo.add(appointment)
        await db_session.commit()

        appointment.confirm()
        await repo.add(appointment)
        await db_session.commit()

        appointment.check_in()
        await repo.add(appointment)
        await db_session.commit()

        appointment.start()
        await repo.add(appointment)
        await db_session.commit()

        appointment.complete(visit_id=visit.id)
        await repo.add(appointment)
        await db_session.commit()

        reloaded = await repo.get_by_id(appointment.id)
        assert reloaded is not None
        assert reloaded.status is AppointmentStatus.COMPLETED
        assert reloaded.checked_in_at is not None
        assert reloaded.completed_at is not None
        assert reloaded.visit_id == visit.id


class TestGetByAppointmentNumber:
    async def test_returns_the_matching_appointment(self, db_session: AsyncSession) -> None:
        organization, patient, doctor = await persist_full_chain(db_session)
        repo = SqlAlchemyAppointmentRepository(db_session)
        appointment_number = f"APT-{uuid4().hex[:12].upper()}"

        appointment = Appointment.create(
            organization_id=organization.id,
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_number=appointment_number,
            appointment_date=date(2026, 3, 1),
            start_time=time(9, 0),
            end_time=time(9, 30),
            appointment_type=AppointmentType.CONSULTATION,
        )
        await repo.add(appointment)
        await db_session.commit()

        found = await repo.get_by_appointment_number(appointment_number)
        assert found is not None and found.id == appointment.id

    async def test_returns_none_for_an_unmatched_number(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyAppointmentRepository(db_session)
        assert await repo.get_by_appointment_number("APT-MISSING") is None


class TestListByPatientAndDoctor:
    async def test_list_by_patient_returns_appointments_ordered_by_date_and_time(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor = await persist_full_chain(db_session)
        repo = SqlAlchemyAppointmentRepository(db_session)

        await repo.add(
            Appointment.create(
                organization_id=organization.id,
                patient_id=patient.id,
                doctor_id=doctor.id,
                appointment_number=f"APT-{uuid4().hex[:12].upper()}",
                appointment_date=date(2026, 3, 2),
                start_time=time(9, 0),
                end_time=time(9, 30),
                appointment_type=AppointmentType.CONSULTATION,
            )
        )
        await repo.add(
            Appointment.create(
                organization_id=organization.id,
                patient_id=patient.id,
                doctor_id=doctor.id,
                appointment_number=f"APT-{uuid4().hex[:12].upper()}",
                appointment_date=date(2026, 3, 1),
                start_time=time(9, 0),
                end_time=time(9, 30),
                appointment_type=AppointmentType.CONSULTATION,
            )
        )
        await db_session.commit()

        appointments = await repo.list_by_patient(patient.id)
        assert [a.appointment_date for a in appointments] == [date(2026, 3, 1), date(2026, 3, 2)]

    async def test_list_by_doctor_returns_appointments_scoped_to_the_doctor(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor = await persist_full_chain(db_session)
        _org2, other_patient, other_doctor = await persist_full_chain(db_session)
        repo = SqlAlchemyAppointmentRepository(db_session)

        await repo.add(
            Appointment.create(
                organization_id=organization.id,
                patient_id=patient.id,
                doctor_id=doctor.id,
                appointment_number=f"APT-{uuid4().hex[:12].upper()}",
                appointment_date=date(2026, 3, 1),
                start_time=time(9, 0),
                end_time=time(9, 30),
                appointment_type=AppointmentType.CONSULTATION,
            )
        )
        await repo.add(
            Appointment.create(
                organization_id=_org2.id,
                patient_id=other_patient.id,
                doctor_id=other_doctor.id,
                appointment_number=f"APT-{uuid4().hex[:12].upper()}",
                appointment_date=date(2026, 3, 1),
                start_time=time(9, 0),
                end_time=time(9, 30),
                appointment_type=AppointmentType.CONSULTATION,
            )
        )
        await db_session.commit()

        appointments = await repo.list_by_doctor(doctor.id)
        assert [a.doctor_id for a in appointments] == [doctor.id]

    async def test_returns_empty_list_for_a_patient_without_appointments(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyAppointmentRepository(db_session)
        assert await repo.list_by_patient(uuid4()) == []

    async def test_returns_empty_list_for_a_doctor_without_appointments(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyAppointmentRepository(db_session)
        assert await repo.list_by_doctor(uuid4()) == []


class TestAppointmentSearch:
    """Search & Filtering module — `SqlAlchemyAppointmentRepository.search`."""

    async def test_scopes_to_organization_and_filters_by_patient_and_doctor(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor = await persist_full_chain(db_session)
        _org2, other_patient, other_doctor = await persist_full_chain(db_session)
        repo = SqlAlchemyAppointmentRepository(db_session)
        appointment = Appointment.create(
            organization_id=organization.id,
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_number=f"APT-{uuid4().hex[:12].upper()}",
            appointment_date=date(2026, 3, 1),
            start_time=time(9, 0),
            end_time=time(9, 30),
            appointment_type=AppointmentType.CONSULTATION,
            reason_for_visit="Annual check-up",
        )
        other = Appointment.create(
            organization_id=_org2.id,
            patient_id=other_patient.id,
            doctor_id=other_doctor.id,
            appointment_number=f"APT-{uuid4().hex[:12].upper()}",
            appointment_date=date(2026, 3, 1),
            start_time=time(9, 0),
            end_time=time(9, 30),
            appointment_type=AppointmentType.CONSULTATION,
        )
        await repo.add(appointment)
        await repo.add(other)
        await db_session.commit()

        results, total = await repo.search(
            organization_id=organization.id, patient_id=patient.id, doctor_id=doctor.id
        )

        assert total == 1
        assert [a.id for a in results] == [appointment.id]

    async def test_query_matches_reason_for_visit_full_text(self, db_session: AsyncSession) -> None:
        organization, patient, doctor = await persist_full_chain(db_session)
        repo = SqlAlchemyAppointmentRepository(db_session)
        appointment = Appointment.create(
            organization_id=organization.id,
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_number=f"APT-{uuid4().hex[:12].upper()}",
            appointment_date=date(2026, 3, 1),
            start_time=time(9, 0),
            end_time=time(9, 30),
            appointment_type=AppointmentType.CONSULTATION,
            reason_for_visit="Persistent migraine headaches",
        )
        await repo.add(appointment)
        await db_session.commit()

        results, total = await repo.search(organization_id=organization.id, query="migraine")

        assert total == 1
        assert [a.id for a in results] == [appointment.id]

    async def test_status_and_appointment_date_range_filters(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor = await persist_full_chain(db_session)
        repo = SqlAlchemyAppointmentRepository(db_session)
        early = Appointment.create(
            organization_id=organization.id,
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_number=f"APT-{uuid4().hex[:12].upper()}",
            appointment_date=date(2026, 1, 1),
            start_time=time(9, 0),
            end_time=time(9, 30),
            appointment_type=AppointmentType.CONSULTATION,
        )
        late = Appointment.create(
            organization_id=organization.id,
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_number=f"APT-{uuid4().hex[:12].upper()}",
            appointment_date=date(2026, 6, 1),
            start_time=time(9, 0),
            end_time=time(9, 30),
            appointment_type=AppointmentType.CONSULTATION,
        )
        late.confirm()
        await repo.add(early)
        await repo.add(late)
        await db_session.commit()

        results, total = await repo.search(
            organization_id=organization.id,
            statuses=[AppointmentStatus.CONFIRMED],
            appointment_date_from=date(2026, 3, 1),
        )

        assert total == 1
        assert [a.id for a in results] == [late.id]


class TestAppointmentNumberUniqueness:
    async def test_duplicate_appointment_number_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor = await persist_full_chain(db_session)
        repo = SqlAlchemyAppointmentRepository(db_session)
        appointment_number = f"APT-{uuid4().hex[:12].upper()}"

        first = Appointment.create(
            organization_id=organization.id,
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_number=appointment_number,
            appointment_date=date(2026, 3, 1),
            start_time=time(9, 0),
            end_time=time(9, 30),
            appointment_type=AppointmentType.CONSULTATION,
        )
        await repo.add(first)
        await db_session.commit()

        second = Appointment.create(
            organization_id=organization.id,
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_number=appointment_number,
            appointment_date=date(2026, 3, 2),
            start_time=time(10, 0),
            end_time=time(10, 30),
            appointment_type=AppointmentType.CONSULTATION,
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_duplicate_number_across_different_organizations_still_violates_uniqueness(
        self, db_session: AsyncSession
    ) -> None:
        """ "Appointment number must be globally unique" — deliberately not
        scoped to `organization_id`."""
        organization_a, patient_a, doctor_a = await persist_full_chain(db_session)
        organization_b, patient_b, doctor_b = await persist_full_chain(db_session)
        repo = SqlAlchemyAppointmentRepository(db_session)
        appointment_number = f"APT-{uuid4().hex[:12].upper()}"

        first = Appointment.create(
            organization_id=organization_a.id,
            patient_id=patient_a.id,
            doctor_id=doctor_a.id,
            appointment_number=appointment_number,
            appointment_date=date(2026, 3, 1),
            start_time=time(9, 0),
            end_time=time(9, 30),
            appointment_type=AppointmentType.CONSULTATION,
        )
        await repo.add(first)
        await db_session.commit()

        second = Appointment.create(
            organization_id=organization_b.id,
            patient_id=patient_b.id,
            doctor_id=doctor_b.id,
            appointment_number=appointment_number,
            appointment_date=date(2026, 3, 1),
            start_time=time(9, 0),
            end_time=time(9, 30),
            appointment_type=AppointmentType.CONSULTATION,
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestAppointmentRequiresValidReferences:
    async def test_nonexistent_organization_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        _organization, patient, doctor = await persist_full_chain(db_session)
        repo = SqlAlchemyAppointmentRepository(db_session)

        appointment = Appointment.create(
            organization_id=uuid4(),
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_number=f"APT-{uuid4().hex[:12].upper()}",
            appointment_date=date(2026, 3, 1),
            start_time=time(9, 0),
            end_time=time(9, 30),
            appointment_type=AppointmentType.CONSULTATION,
        )
        await repo.add(appointment)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_patient_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, doctor = await persist_full_chain(db_session)
        repo = SqlAlchemyAppointmentRepository(db_session)

        appointment = Appointment.create(
            organization_id=organization.id,
            patient_id=uuid4(),
            doctor_id=doctor.id,
            appointment_number=f"APT-{uuid4().hex[:12].upper()}",
            appointment_date=date(2026, 3, 1),
            start_time=time(9, 0),
            end_time=time(9, 30),
            appointment_type=AppointmentType.CONSULTATION,
        )
        await repo.add(appointment)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_doctor_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, _doctor = await persist_full_chain(db_session)
        repo = SqlAlchemyAppointmentRepository(db_session)

        appointment = Appointment.create(
            organization_id=organization.id,
            patient_id=patient.id,
            doctor_id=uuid4(),
            appointment_number=f"APT-{uuid4().hex[:12].upper()}",
            appointment_date=date(2026, 3, 1),
            start_time=time(9, 0),
            end_time=time(9, 30),
            appointment_type=AppointmentType.CONSULTATION,
        )
        await repo.add(appointment)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_booked_by_user_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor = await persist_full_chain(db_session)
        repo = SqlAlchemyAppointmentRepository(db_session)

        appointment = Appointment.create(
            organization_id=organization.id,
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_number=f"APT-{uuid4().hex[:12].upper()}",
            appointment_date=date(2026, 3, 1),
            start_time=time(9, 0),
            end_time=time(9, 30),
            appointment_type=AppointmentType.CONSULTATION,
            booked_by_user_id=uuid4(),
        )
        await repo.add(appointment)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestCheckConstraints:
    """`Appointment.__post_init__` already prevents `end_time <=
    start_time` from ever existing via the domain layer — this test
    targets the DB `CHECK` constraint directly (bypassing the domain
    entity, the way a direct SQL edit would) to prove the
    defense-in-depth layer actually works, the same pattern
    `tests.integration.modules.differential_diagnosis
    .test_differential_diagnosis_repository.TestCheckConstraints`
    already established.
    """

    async def test_end_time_not_after_start_time_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor = await persist_full_chain(db_session)

        model = AppointmentModel(
            organization_id=organization.id,
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_number=f"APT-{uuid4().hex[:12].upper()}",
            appointment_date=date(2026, 3, 1),
            start_time=time(9, 30),
            end_time=time(9, 0),
            appointment_type=AppointmentType.CONSULTATION,
            status=AppointmentStatus.SCHEDULED,
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
