"""Integration tests for `SqlAlchemyVisitProcedureRepository`, including
the FKs to `organizations`/`patient_visits`/`doctors`, the per-visit
`sequence_number` uniqueness constraint, and the status/`performed_at`
consistency `CHECK` constraints, against a real PostgreSQL instance."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.procedures._helpers import (
    persist_doctor,
    persist_organization,
    persist_patient,
    persist_visit,
)

from app.modules.doctor.domain.entities import Doctor
from app.modules.organization.domain.entities import Organization
from app.modules.patient.domain.entities import Patient
from app.modules.procedures.domain.entities import VisitProcedure
from app.modules.procedures.domain.enums import ProcedureStatus
from app.modules.procedures.infrastructure.models import VisitProcedureModel
from app.modules.procedures.infrastructure.repositories import SqlAlchemyVisitProcedureRepository
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


class TestVisitProcedureRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, _patient, doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitProcedureRepository(db_session)

        procedure = VisitProcedure.create(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=1,
            procedure_name="Wound dressing",
            procedure_code="P-001",
            procedure_category="Minor surgery",
            procedure_status=ProcedureStatus.COMPLETED,
            performed_by=doctor.id,
            performed_at=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
            notes="Performed under local anesthesia",
        )
        await repo.add(procedure)
        await db_session.commit()

        reloaded = await repo.get_by_id(procedure.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.visit_id == visit.id
        assert reloaded.sequence_number == 1
        assert reloaded.procedure_name == "Wound dressing"
        assert reloaded.procedure_code == "P-001"
        assert reloaded.procedure_category == "Minor surgery"
        assert reloaded.procedure_status is ProcedureStatus.COMPLETED
        assert reloaded.performed_by == doctor.id
        assert reloaded.performed_at == datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
        assert reloaded.notes == "Performed under local anesthesia"

    async def test_optional_fields_round_trip_as_none(self, db_session: AsyncSession) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitProcedureRepository(db_session)

        procedure = VisitProcedure.create(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=1,
            procedure_name="Suturing",
        )
        await repo.add(procedure)
        await db_session.commit()

        reloaded = await repo.get_by_id(procedure.id)
        assert reloaded is not None
        assert reloaded.procedure_code is None
        assert reloaded.procedure_category is None
        assert reloaded.procedure_status is ProcedureStatus.PLANNED
        assert reloaded.performed_by is None
        assert reloaded.performed_at is None
        assert reloaded.notes is None


class TestGetByVisitAndSequence:
    async def test_returns_the_matching_procedure(self, db_session: AsyncSession) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitProcedureRepository(db_session)

        procedure = VisitProcedure.create(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=1,
            procedure_name="Suturing",
        )
        await repo.add(procedure)
        await db_session.commit()

        found = await repo.get_by_visit_and_sequence(visit_id=visit.id, sequence_number=1)
        assert found is not None and found.id == procedure.id

    async def test_returns_none_for_a_nonexistent_sequence(self, db_session: AsyncSession) -> None:
        _organization, _patient, _doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitProcedureRepository(db_session)

        found = await repo.get_by_visit_and_sequence(visit_id=visit.id, sequence_number=99)
        assert found is None


class TestListByVisit:
    async def test_returns_procedures_ordered_by_sequence_number_scoped_to_the_visit(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit_a = await _persist_full_chain(db_session)
        visit_b = await persist_visit(
            db_session, organization_id=organization.id, patient_id=patient.id, doctor_id=doctor.id
        )
        repo = SqlAlchemyVisitProcedureRepository(db_session)

        await repo.add(
            VisitProcedure.create(
                organization_id=organization.id,
                visit_id=visit_a.id,
                sequence_number=2,
                procedure_name="Suturing",
            )
        )
        await repo.add(
            VisitProcedure.create(
                organization_id=organization.id,
                visit_id=visit_a.id,
                sequence_number=1,
                procedure_name="Wound dressing",
            )
        )
        await repo.add(
            VisitProcedure.create(
                organization_id=organization.id,
                visit_id=visit_b.id,
                sequence_number=1,
                procedure_name="Unrelated procedure",
            )
        )
        await db_session.commit()

        procedures = await repo.list_by_visit(visit_a.id)
        assert [p.sequence_number for p in procedures] == [1, 2]
        assert [p.procedure_name for p in procedures] == ["Wound dressing", "Suturing"]


class TestSequenceNumberUniqueness:
    async def test_duplicate_sequence_number_within_the_same_visit_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitProcedureRepository(db_session)

        first = VisitProcedure.create(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=1,
            procedure_name="Wound dressing",
        )
        await repo.add(first)
        await db_session.commit()

        second = VisitProcedure.create(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=1,
            procedure_name="Suturing",
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestVisitProcedureRequiresValidReferences:
    async def test_nonexistent_visit_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyVisitProcedureRepository(db_session)

        procedure = VisitProcedure.create(
            organization_id=organization.id,
            visit_id=uuid4(),
            sequence_number=1,
            procedure_name="Orphaned procedure",
        )
        await repo.add(procedure)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_performed_by_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitProcedureRepository(db_session)

        procedure = VisitProcedure.create(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=1,
            procedure_name="Orphaned attribution",
            performed_by=uuid4(),
        )
        await repo.add(procedure)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestCheckConstraints:
    """`VisitProcedure.__post_init__` already prevents these states from
    ever existing via the domain layer — these tests target the DB
    `CHECK` constraints directly (bypassing the domain entity, the way a
    direct SQL edit would) to prove the defense-in-depth layer actually
    works, the same pattern
    `tests.integration.modules.diagnosis.test_visit_diagnosis_repository.TestCheckConstraints`
    already established."""

    async def test_sequence_number_below_one_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)

        model = VisitProcedureModel(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=0,
            procedure_name="Bad sequence",
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_completed_without_performed_at_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)

        model = VisitProcedureModel(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=1,
            procedure_name="Bad completion",
            procedure_status=ProcedureStatus.COMPLETED,
            performed_at=None,
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_cancelled_with_performed_at_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)

        model = VisitProcedureModel(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=1,
            procedure_name="Bad cancellation",
            procedure_status=ProcedureStatus.CANCELLED,
            performed_at=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
