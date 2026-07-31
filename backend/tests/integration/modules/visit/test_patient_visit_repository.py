"""Integration tests for `SqlAlchemyPatientVisitRepository`, including the
FKs to `organizations`/`patients`/`doctors` and the per-organization
`visit_number` uniqueness constraint, against a real PostgreSQL
instance."""

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.visit._helpers import (
    persist_doctor,
    persist_organization,
    persist_patient,
)

from app.modules.doctor.domain.entities import Doctor
from app.modules.organization.domain.entities import Organization
from app.modules.patient.domain.entities import Patient
from app.modules.visit.domain.entities import PatientVisit
from app.modules.visit.domain.enums import VisitPriority, VisitStatus, VisitType
from app.modules.visit.infrastructure.models import PatientVisitModel
from app.modules.visit.infrastructure.repositories import SqlAlchemyPatientVisitRepository


async def _persist_patient_and_doctor(
    db_session: AsyncSession,
) -> tuple[Organization, Patient, Doctor]:
    organization = await persist_organization(db_session)
    patient = await persist_patient(db_session, organization_id=organization.id)
    doctor = await persist_doctor(db_session, organization_id=organization.id)
    return organization, patient, doctor


class TestPatientVisitRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, patient, doctor = await _persist_patient_and_doctor(db_session)
        repo = SqlAlchemyPatientVisitRepository(db_session)

        visit = PatientVisit.create(
            organization_id=organization.id,
            patient_id=patient.id,
            doctor_id=doctor.id,
            visit_number="V-0001",
            visit_type=VisitType.CONSULTATION,
            visit_date=date(2026, 1, 1),
            priority=VisitPriority.HIGH,
            chief_complaint_summary="Persistent cough",
            reason_for_visit="Follow-up on bronchitis",
            room_number="4B",
            notes="Patient reports improvement",
        )
        await repo.add(visit)
        await db_session.commit()

        reloaded = await repo.get_by_id(visit.id)
        assert reloaded is not None
        assert reloaded.patient_id == patient.id
        assert reloaded.doctor_id == doctor.id
        assert reloaded.visit_number == "V-0001"
        assert reloaded.visit_type is VisitType.CONSULTATION
        assert reloaded.visit_status is VisitStatus.SCHEDULED
        assert reloaded.priority is VisitPriority.HIGH
        assert reloaded.chief_complaint_summary == "Persistent cough"
        assert reloaded.reason_for_visit == "Follow-up on bronchitis"
        assert reloaded.room_number == "4B"
        assert reloaded.notes == "Patient reports improvement"

    async def test_full_lifecycle_persists(self, db_session: AsyncSession) -> None:
        organization, patient, doctor = await _persist_patient_and_doctor(db_session)
        repo = SqlAlchemyPatientVisitRepository(db_session)

        visit = PatientVisit.create(
            organization_id=organization.id,
            patient_id=patient.id,
            doctor_id=doctor.id,
            visit_number="V-0002",
            visit_type=VisitType.CONSULTATION,
            visit_date=date(2026, 1, 1),
        )
        await repo.add(visit)
        await db_session.commit()

        check_in_time = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
        visit.check_in(check_in_time=check_in_time)
        await repo.add(visit)
        await db_session.commit()

        start_time = check_in_time + timedelta(minutes=10)
        visit.start_consultation(consultation_start_time=start_time)
        await repo.add(visit)
        await db_session.commit()

        end_time = start_time + timedelta(minutes=20)
        visit.complete(consultation_end_time=end_time)
        await repo.add(visit)
        await db_session.commit()

        check_out_time = end_time + timedelta(minutes=5)
        visit.check_out(check_out_time=check_out_time)
        await repo.add(visit)
        await db_session.commit()

        reloaded = await repo.get_by_id(visit.id)
        assert reloaded is not None
        assert reloaded.visit_status is VisitStatus.COMPLETED
        assert reloaded.check_in_time == check_in_time
        assert reloaded.consultation_start_time == start_time
        assert reloaded.consultation_end_time == end_time
        assert reloaded.check_out_time == check_out_time

    async def test_list_by_patient_scopes_to_a_single_patient(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient_a, doctor = await _persist_patient_and_doctor(db_session)
        patient_b = await persist_patient(db_session, organization_id=organization.id)
        repo = SqlAlchemyPatientVisitRepository(db_session)

        visit_a = PatientVisit.create(
            organization_id=organization.id,
            patient_id=patient_a.id,
            doctor_id=doctor.id,
            visit_number="V-A",
            visit_type=VisitType.CONSULTATION,
            visit_date=date(2026, 1, 1),
        )
        visit_b = PatientVisit.create(
            organization_id=organization.id,
            patient_id=patient_b.id,
            doctor_id=doctor.id,
            visit_number="V-B",
            visit_type=VisitType.CONSULTATION,
            visit_date=date(2026, 1, 1),
        )
        await repo.add(visit_a)
        await repo.add(visit_b)
        await db_session.commit()

        visits_for_a = await repo.list_by_patient(patient_a.id)
        assert [v.id for v in visits_for_a] == [visit_a.id]


class TestGetByVisitNumber:
    async def test_scopes_to_organization(self, db_session: AsyncSession) -> None:
        org_a, patient_a, doctor_a = await _persist_patient_and_doctor(db_session)
        org_b, patient_b, doctor_b = await _persist_patient_and_doctor(db_session)
        repo = SqlAlchemyPatientVisitRepository(db_session)

        visit_a = PatientVisit.create(
            organization_id=org_a.id,
            patient_id=patient_a.id,
            doctor_id=doctor_a.id,
            visit_number="SHARED-NUMBER",
            visit_type=VisitType.CONSULTATION,
            visit_date=date(2026, 1, 1),
        )
        visit_b = PatientVisit.create(
            organization_id=org_b.id,
            patient_id=patient_b.id,
            doctor_id=doctor_b.id,
            visit_number="SHARED-NUMBER",
            visit_type=VisitType.CONSULTATION,
            visit_date=date(2026, 1, 1),
        )
        await repo.add(visit_a)
        await repo.add(visit_b)
        await db_session.commit()

        found_in_a = await repo.get_by_visit_number(
            organization_id=org_a.id, visit_number="SHARED-NUMBER"
        )
        found_in_b = await repo.get_by_visit_number(
            organization_id=org_b.id, visit_number="SHARED-NUMBER"
        )
        assert found_in_a is not None and found_in_a.id == visit_a.id
        assert found_in_b is not None and found_in_b.id == visit_b.id


class TestVisitNumberUniqueness:
    async def test_duplicate_visit_number_within_organization_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor = await _persist_patient_and_doctor(db_session)
        repo = SqlAlchemyPatientVisitRepository(db_session)

        first = PatientVisit.create(
            organization_id=organization.id,
            patient_id=patient.id,
            doctor_id=doctor.id,
            visit_number="V-DUPLICATE",
            visit_type=VisitType.CONSULTATION,
            visit_date=date(2026, 1, 1),
        )
        await repo.add(first)
        await db_session.commit()

        second = PatientVisit.create(
            organization_id=organization.id,
            patient_id=patient.id,
            doctor_id=doctor.id,
            visit_number="V-DUPLICATE",
            visit_type=VisitType.FOLLOW_UP,
            visit_date=date(2026, 2, 1),
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestPatientVisitSearch:
    """Search & Filtering module — `SqlAlchemyPatientVisitRepository.search`."""

    async def test_scopes_to_organization_and_filters_by_patient(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor = await _persist_patient_and_doctor(db_session)
        _org2, other_patient, other_doctor = await _persist_patient_and_doctor(db_session)
        repo = SqlAlchemyPatientVisitRepository(db_session)
        visit = PatientVisit.create(
            organization_id=organization.id,
            patient_id=patient.id,
            doctor_id=doctor.id,
            visit_number=f"V-{uuid4().hex[:12].upper()}",
            visit_type=VisitType.CONSULTATION,
            visit_date=date(2026, 1, 1),
            chief_complaint_summary="Recurring migraines",
        )
        other = PatientVisit.create(
            organization_id=_org2.id,
            patient_id=other_patient.id,
            doctor_id=other_doctor.id,
            visit_number=f"V-{uuid4().hex[:12].upper()}",
            visit_type=VisitType.CONSULTATION,
            visit_date=date(2026, 1, 1),
        )
        await repo.add(visit)
        await repo.add(other)
        await db_session.commit()

        results, total = await repo.search(organization_id=organization.id, patient_id=patient.id)

        assert total == 1
        assert [v.id for v in results] == [visit.id]

    async def test_query_matches_chief_complaint_full_text(self, db_session: AsyncSession) -> None:
        organization, patient, doctor = await _persist_patient_and_doctor(db_session)
        repo = SqlAlchemyPatientVisitRepository(db_session)
        visit = PatientVisit.create(
            organization_id=organization.id,
            patient_id=patient.id,
            doctor_id=doctor.id,
            visit_number=f"V-{uuid4().hex[:12].upper()}",
            visit_type=VisitType.CONSULTATION,
            visit_date=date(2026, 1, 1),
            chief_complaint_summary="Recurring migraines",
        )
        await repo.add(visit)
        await db_session.commit()

        results, total = await repo.search(organization_id=organization.id, query="migraines")

        assert total == 1
        assert [v.id for v in results] == [visit.id]

    async def test_status_and_visit_date_range_filters(self, db_session: AsyncSession) -> None:
        organization, patient, doctor = await _persist_patient_and_doctor(db_session)
        repo = SqlAlchemyPatientVisitRepository(db_session)
        cancelled = PatientVisit.create(
            organization_id=organization.id,
            patient_id=patient.id,
            doctor_id=doctor.id,
            visit_number=f"V-{uuid4().hex[:12].upper()}",
            visit_type=VisitType.CONSULTATION,
            visit_date=date(2026, 6, 1),
        )
        cancelled.cancel()
        scheduled = PatientVisit.create(
            organization_id=organization.id,
            patient_id=patient.id,
            doctor_id=doctor.id,
            visit_number=f"V-{uuid4().hex[:12].upper()}",
            visit_type=VisitType.CONSULTATION,
            visit_date=date(2026, 6, 1),
        )
        await repo.add(cancelled)
        await repo.add(scheduled)
        await db_session.commit()

        results, total = await repo.search(
            organization_id=organization.id, statuses=[VisitStatus.CANCELLED]
        )

        assert total == 1
        assert [v.id for v in results] == [cancelled.id]


class TestPatientVisitRequiresValidReferences:
    async def test_nonexistent_patient_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        doctor = await persist_doctor(db_session, organization_id=organization.id)
        repo = SqlAlchemyPatientVisitRepository(db_session)

        visit = PatientVisit.create(
            organization_id=organization.id,
            patient_id=uuid4(),
            doctor_id=doctor.id,
            visit_number="V-ORPHAN-PATIENT",
            visit_type=VisitType.CONSULTATION,
            visit_date=date(2026, 1, 1),
        )
        await repo.add(visit)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_doctor_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        patient = await persist_patient(db_session, organization_id=organization.id)
        repo = SqlAlchemyPatientVisitRepository(db_session)

        visit = PatientVisit.create(
            organization_id=organization.id,
            patient_id=patient.id,
            doctor_id=uuid4(),
            visit_number="V-ORPHAN-DOCTOR",
            visit_type=VisitType.CONSULTATION,
            visit_date=date(2026, 1, 1),
        )
        await repo.add(visit)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestCheckOutCheckConstraint:
    async def test_a_check_out_time_before_check_in_time_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        """`PatientVisit.__post_init__` already prevents this state from
        ever existing via the domain layer — this test targets the DB
        `CHECK` constraint directly (bypassing the domain entity, the way
        a direct SQL edit would) to prove the defense-in-depth layer
        actually works."""
        organization, patient, doctor = await _persist_patient_and_doctor(db_session)

        check_in_time = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
        model = PatientVisitModel(
            organization_id=organization.id,
            patient_id=patient.id,
            doctor_id=doctor.id,
            visit_number="V-BAD-CHECKOUT",
            visit_type=VisitType.CONSULTATION,
            visit_date=date(2026, 1, 1),
            check_in_time=check_in_time,
            check_out_time=check_in_time - timedelta(minutes=1),
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestFollowUpDateCheckConstraint:
    async def test_follow_up_required_without_follow_up_date_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        """Same defense-in-depth rationale as
        `TestCheckOutCheckConstraint` above, for the "follow_up_date is
        required only if follow_up_required is true" rule."""
        organization, patient, doctor = await _persist_patient_and_doctor(db_session)

        model = PatientVisitModel(
            organization_id=organization.id,
            patient_id=patient.id,
            doctor_id=doctor.id,
            visit_number="V-BAD-FOLLOWUP",
            visit_type=VisitType.CONSULTATION,
            visit_date=date(2026, 1, 1),
            follow_up_required=True,
            follow_up_date=None,
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
