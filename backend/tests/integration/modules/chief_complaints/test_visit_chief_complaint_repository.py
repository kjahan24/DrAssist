"""Integration tests for `SqlAlchemyVisitChiefComplaintRepository`,
including the FKs to `organizations`/`patient_visits`/`doctors`, the
per-visit `sequence_number` uniqueness constraint, and the numeric-range
`CHECK` constraints, against a real PostgreSQL instance."""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.chief_complaints._helpers import (
    persist_doctor,
    persist_organization,
    persist_patient,
    persist_visit,
)

from app.modules.chief_complaints.domain.entities import VisitChiefComplaint
from app.modules.chief_complaints.domain.enums import DurationUnit, Onset, Severity
from app.modules.chief_complaints.infrastructure.models import VisitChiefComplaintModel
from app.modules.chief_complaints.infrastructure.repositories import (
    SqlAlchemyVisitChiefComplaintRepository,
)
from app.modules.doctor.domain.entities import Doctor
from app.modules.organization.domain.entities import Organization
from app.modules.patient.domain.entities import Patient
from app.modules.visit.domain.entities import PatientVisit


async def _persist_full_chain(
    db_session: AsyncSession,
) -> tuple[Organization, Patient, Doctor, PatientVisit]:
    organization = await persist_organization(db_session)
    patient = await persist_patient(db_session, organization_id=organization.id)
    doctor = await persist_doctor(db_session, organization_id=organization.id)
    visit = await persist_visit(
        db_session, organization_id=organization.id, patient_id=patient.id, doctor_id=doctor.id
    )
    return organization, patient, doctor, visit


class TestVisitChiefComplaintRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, _patient, doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitChiefComplaintRepository(db_session)

        chief_complaint = VisitChiefComplaint.create(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=1,
            complaint="Persistent cough",
            recorded_at=datetime(2026, 1, 1, 9, 0),
            duration_value=3,
            duration_unit=DurationUnit.DAYS,
            severity=Severity.MODERATE,
            onset=Onset.GRADUAL,
            notes="Worse at night",
            recorded_by=doctor.id,
        )
        await repo.add(chief_complaint)
        await db_session.commit()

        reloaded = await repo.get_by_id(chief_complaint.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.visit_id == visit.id
        assert reloaded.sequence_number == 1
        assert reloaded.complaint == "Persistent cough"
        assert reloaded.duration_value == 3
        assert reloaded.duration_unit is DurationUnit.DAYS
        assert reloaded.severity is Severity.MODERATE
        assert reloaded.onset is Onset.GRADUAL
        assert reloaded.notes == "Worse at night"
        assert reloaded.recorded_by == doctor.id

    async def test_optional_fields_round_trip_as_none(self, db_session: AsyncSession) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitChiefComplaintRepository(db_session)

        chief_complaint = VisitChiefComplaint.create(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=1,
            complaint="Headache",
            recorded_at=datetime(2026, 1, 1, 9, 0),
        )
        await repo.add(chief_complaint)
        await db_session.commit()

        reloaded = await repo.get_by_id(chief_complaint.id)
        assert reloaded is not None
        assert reloaded.duration_value is None
        assert reloaded.duration_unit is None
        assert reloaded.severity is None
        assert reloaded.onset is None
        assert reloaded.notes is None
        assert reloaded.recorded_by is None


class TestGetByVisitAndSequence:
    async def test_returns_the_matching_complaint(self, db_session: AsyncSession) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitChiefComplaintRepository(db_session)

        chief_complaint = VisitChiefComplaint.create(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=1,
            complaint="Sore throat",
            recorded_at=datetime(2026, 1, 1, 9, 0),
        )
        await repo.add(chief_complaint)
        await db_session.commit()

        found = await repo.get_by_visit_and_sequence(visit_id=visit.id, sequence_number=1)
        assert found is not None and found.id == chief_complaint.id

    async def test_returns_none_for_a_nonexistent_sequence(self, db_session: AsyncSession) -> None:
        _organization, _patient, _doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitChiefComplaintRepository(db_session)

        found = await repo.get_by_visit_and_sequence(visit_id=visit.id, sequence_number=99)
        assert found is None


class TestListByVisit:
    async def test_returns_complaints_ordered_by_sequence_number_scoped_to_the_visit(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit_a = await _persist_full_chain(db_session)
        visit_b = await persist_visit(
            db_session, organization_id=organization.id, patient_id=patient.id, doctor_id=doctor.id
        )
        repo = SqlAlchemyVisitChiefComplaintRepository(db_session)

        await repo.add(
            VisitChiefComplaint.create(
                organization_id=organization.id,
                visit_id=visit_a.id,
                sequence_number=2,
                complaint="Fatigue",
                recorded_at=datetime(2026, 1, 1, 9, 0),
            )
        )
        await repo.add(
            VisitChiefComplaint.create(
                organization_id=organization.id,
                visit_id=visit_a.id,
                sequence_number=1,
                complaint="Fever",
                recorded_at=datetime(2026, 1, 1, 9, 0),
            )
        )
        await repo.add(
            VisitChiefComplaint.create(
                organization_id=organization.id,
                visit_id=visit_b.id,
                sequence_number=1,
                complaint="Unrelated complaint",
                recorded_at=datetime(2026, 1, 1, 9, 0),
            )
        )
        await db_session.commit()

        complaints = await repo.list_by_visit(visit_a.id)
        assert [c.sequence_number for c in complaints] == [1, 2]
        assert [c.complaint for c in complaints] == ["Fever", "Fatigue"]


class TestSequenceNumberUniqueness:
    async def test_duplicate_sequence_number_within_the_same_visit_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitChiefComplaintRepository(db_session)

        first = VisitChiefComplaint.create(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=1,
            complaint="Nausea",
            recorded_at=datetime(2026, 1, 1, 9, 0),
        )
        await repo.add(first)
        await db_session.commit()

        second = VisitChiefComplaint.create(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=1,
            complaint="Dizziness",
            recorded_at=datetime(2026, 1, 1, 9, 5),
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestVisitChiefComplaintRequiresValidReferences:
    async def test_nonexistent_visit_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyVisitChiefComplaintRepository(db_session)

        chief_complaint = VisitChiefComplaint.create(
            organization_id=organization.id,
            visit_id=uuid4(),
            sequence_number=1,
            complaint="Orphaned complaint",
            recorded_at=datetime(2026, 1, 1, 9, 0),
        )
        await repo.add(chief_complaint)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_recorded_by_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitChiefComplaintRepository(db_session)

        chief_complaint = VisitChiefComplaint.create(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=1,
            complaint="Orphaned attribution",
            recorded_at=datetime(2026, 1, 1, 9, 0),
            recorded_by=uuid4(),
        )
        await repo.add(chief_complaint)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestNumericRangeCheckConstraints:
    """`VisitChiefComplaint.__post_init__` already prevents these states
    from ever existing via the domain layer — these tests target the DB
    `CHECK` constraints directly (bypassing the domain entity, the way a
    direct SQL edit would) to prove the defense-in-depth layer actually
    works, the same pattern
    `tests.integration.modules.vital_signs.test_visit_vital_signs_repository.TestNumericRangeCheckConstraints`
    already established."""

    async def test_sequence_number_below_one_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)

        model = VisitChiefComplaintModel(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=0,
            complaint="Bad sequence",
            recorded_at=datetime(2026, 1, 1, 9, 0),
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_negative_duration_value_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)

        model = VisitChiefComplaintModel(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=1,
            complaint="Bad duration",
            duration_value=-1,
            recorded_at=datetime(2026, 1, 1, 9, 0),
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_duration_unit_without_duration_value_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)

        model = VisitChiefComplaintModel(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=1,
            complaint="Bad duration unit",
            duration_value=None,
            duration_unit=DurationUnit.DAYS,
            recorded_at=datetime(2026, 1, 1, 9, 0),
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
