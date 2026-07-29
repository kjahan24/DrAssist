"""Integration tests for `SqlAlchemyVisitDiagnosisRepository`, including
the FKs to `organizations`/`patient_visits`/`doctors`, the per-visit
`sequence_number` uniqueness constraint, the "one Primary diagnosis per
visit" uniqueness constraint, and the "Ruled Out cannot be Primary" check
constraint, against a real PostgreSQL instance."""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.diagnosis._helpers import (
    persist_doctor,
    persist_organization,
    persist_patient,
    persist_visit,
)

from app.modules.diagnosis.domain.entities import VisitDiagnosis
from app.modules.diagnosis.domain.enums import DiagnosisStatus, DiagnosisType
from app.modules.diagnosis.infrastructure.models import VisitDiagnosisModel
from app.modules.diagnosis.infrastructure.repositories import SqlAlchemyVisitDiagnosisRepository
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


class TestVisitDiagnosisRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, _patient, doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitDiagnosisRepository(db_session)

        diagnosis = VisitDiagnosis.create(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=1,
            diagnosis_name="Type 2 diabetes",
            diagnosis_type=DiagnosisType.PRIMARY,
            diagnosed_at=datetime(2026, 1, 1, 9, 0),
            icd10_code="E11.9",
            diagnosis_status=DiagnosisStatus.CONFIRMED,
            clinical_notes="Diet-controlled",
            diagnosed_by=doctor.id,
        )
        await repo.add(diagnosis)
        await db_session.commit()

        reloaded = await repo.get_by_id(diagnosis.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.visit_id == visit.id
        assert reloaded.sequence_number == 1
        assert reloaded.diagnosis_name == "Type 2 diabetes"
        assert reloaded.diagnosis_type is DiagnosisType.PRIMARY
        assert reloaded.icd10_code == "E11.9"
        assert reloaded.diagnosis_status is DiagnosisStatus.CONFIRMED
        assert reloaded.clinical_notes == "Diet-controlled"
        assert reloaded.diagnosed_by == doctor.id

    async def test_optional_fields_round_trip_as_none(self, db_session: AsyncSession) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitDiagnosisRepository(db_session)

        diagnosis = VisitDiagnosis.create(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=1,
            diagnosis_name="Migraine",
            diagnosis_type=DiagnosisType.SECONDARY,
            diagnosed_at=datetime(2026, 1, 1, 9, 0),
        )
        await repo.add(diagnosis)
        await db_session.commit()

        reloaded = await repo.get_by_id(diagnosis.id)
        assert reloaded is not None
        assert reloaded.icd10_code is None
        assert reloaded.clinical_notes is None
        assert reloaded.diagnosed_by is None
        assert reloaded.diagnosis_status is DiagnosisStatus.PROVISIONAL


class TestGetByVisitAndSequence:
    async def test_returns_the_matching_diagnosis(self, db_session: AsyncSession) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitDiagnosisRepository(db_session)

        diagnosis = VisitDiagnosis.create(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=1,
            diagnosis_name="Asthma",
            diagnosis_type=DiagnosisType.SECONDARY,
            diagnosed_at=datetime(2026, 1, 1, 9, 0),
        )
        await repo.add(diagnosis)
        await db_session.commit()

        found = await repo.get_by_visit_and_sequence(visit_id=visit.id, sequence_number=1)
        assert found is not None and found.id == diagnosis.id

    async def test_returns_none_for_a_nonexistent_sequence(self, db_session: AsyncSession) -> None:
        _organization, _patient, _doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitDiagnosisRepository(db_session)

        found = await repo.get_by_visit_and_sequence(visit_id=visit.id, sequence_number=99)
        assert found is None


class TestGetPrimaryForVisit:
    async def test_returns_the_primary_diagnosis(self, db_session: AsyncSession) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitDiagnosisRepository(db_session)

        primary = VisitDiagnosis.create(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=1,
            diagnosis_name="Type 2 diabetes",
            diagnosis_type=DiagnosisType.PRIMARY,
            diagnosed_at=datetime(2026, 1, 1, 9, 0),
        )
        secondary = VisitDiagnosis.create(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=2,
            diagnosis_name="Hypertension",
            diagnosis_type=DiagnosisType.SECONDARY,
            diagnosed_at=datetime(2026, 1, 1, 9, 0),
        )
        await repo.add(primary)
        await repo.add(secondary)
        await db_session.commit()

        found = await repo.get_primary_for_visit(visit.id)
        assert found is not None and found.id == primary.id

    async def test_returns_none_when_no_primary_diagnosis_exists(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitDiagnosisRepository(db_session)

        await repo.add(
            VisitDiagnosis.create(
                organization_id=organization.id,
                visit_id=visit.id,
                sequence_number=1,
                diagnosis_name="Hypertension",
                diagnosis_type=DiagnosisType.SECONDARY,
                diagnosed_at=datetime(2026, 1, 1, 9, 0),
            )
        )
        await db_session.commit()

        assert await repo.get_primary_for_visit(visit.id) is None


class TestListByVisit:
    async def test_returns_diagnoses_ordered_by_sequence_number_scoped_to_the_visit(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit_a = await _persist_full_chain(db_session)
        visit_b = await persist_visit(
            db_session, organization_id=organization.id, patient_id=patient.id, doctor_id=doctor.id
        )
        repo = SqlAlchemyVisitDiagnosisRepository(db_session)

        await repo.add(
            VisitDiagnosis.create(
                organization_id=organization.id,
                visit_id=visit_a.id,
                sequence_number=2,
                diagnosis_name="Hypertension",
                diagnosis_type=DiagnosisType.SECONDARY,
                diagnosed_at=datetime(2026, 1, 1, 9, 0),
            )
        )
        await repo.add(
            VisitDiagnosis.create(
                organization_id=organization.id,
                visit_id=visit_a.id,
                sequence_number=1,
                diagnosis_name="Type 2 diabetes",
                diagnosis_type=DiagnosisType.PRIMARY,
                diagnosed_at=datetime(2026, 1, 1, 9, 0),
            )
        )
        await repo.add(
            VisitDiagnosis.create(
                organization_id=organization.id,
                visit_id=visit_b.id,
                sequence_number=1,
                diagnosis_name="Unrelated diagnosis",
                diagnosis_type=DiagnosisType.PRIMARY,
                diagnosed_at=datetime(2026, 1, 1, 9, 0),
            )
        )
        await db_session.commit()

        diagnoses = await repo.list_by_visit(visit_a.id)
        assert [d.sequence_number for d in diagnoses] == [1, 2]
        assert [d.diagnosis_name for d in diagnoses] == ["Type 2 diabetes", "Hypertension"]


class TestSequenceNumberUniqueness:
    async def test_duplicate_sequence_number_within_the_same_visit_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitDiagnosisRepository(db_session)

        first = VisitDiagnosis.create(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=1,
            diagnosis_name="Type 2 diabetes",
            diagnosis_type=DiagnosisType.PRIMARY,
            diagnosed_at=datetime(2026, 1, 1, 9, 0),
        )
        await repo.add(first)
        await db_session.commit()

        second = VisitDiagnosis.create(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=1,
            diagnosis_name="Hypertension",
            diagnosis_type=DiagnosisType.SECONDARY,
            diagnosed_at=datetime(2026, 1, 1, 9, 5),
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestPrimaryDiagnosisUniqueness:
    async def test_second_primary_diagnosis_for_the_same_visit_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitDiagnosisRepository(db_session)

        first = VisitDiagnosis.create(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=1,
            diagnosis_name="Type 2 diabetes",
            diagnosis_type=DiagnosisType.PRIMARY,
            diagnosed_at=datetime(2026, 1, 1, 9, 0),
        )
        await repo.add(first)
        await db_session.commit()

        second = VisitDiagnosis.create(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=2,
            diagnosis_name="Acute pancreatitis",
            diagnosis_type=DiagnosisType.PRIMARY,
            diagnosed_at=datetime(2026, 1, 1, 9, 5),
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_primary_diagnosis_on_different_visits_is_allowed(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit_a = await _persist_full_chain(db_session)
        visit_b = await persist_visit(
            db_session, organization_id=organization.id, patient_id=patient.id, doctor_id=doctor.id
        )
        repo = SqlAlchemyVisitDiagnosisRepository(db_session)

        await repo.add(
            VisitDiagnosis.create(
                organization_id=organization.id,
                visit_id=visit_a.id,
                sequence_number=1,
                diagnosis_name="Type 2 diabetes",
                diagnosis_type=DiagnosisType.PRIMARY,
                diagnosed_at=datetime(2026, 1, 1, 9, 0),
            )
        )
        await repo.add(
            VisitDiagnosis.create(
                organization_id=organization.id,
                visit_id=visit_b.id,
                sequence_number=1,
                diagnosis_name="Acute pancreatitis",
                diagnosis_type=DiagnosisType.PRIMARY,
                diagnosed_at=datetime(2026, 1, 1, 9, 0),
            )
        )
        await db_session.commit()

        assert await repo.get_primary_for_visit(visit_a.id) is not None
        assert await repo.get_primary_for_visit(visit_b.id) is not None


class TestVisitDiagnosisRequiresValidReferences:
    async def test_nonexistent_visit_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyVisitDiagnosisRepository(db_session)

        diagnosis = VisitDiagnosis.create(
            organization_id=organization.id,
            visit_id=uuid4(),
            sequence_number=1,
            diagnosis_name="Orphaned diagnosis",
            diagnosis_type=DiagnosisType.PRIMARY,
            diagnosed_at=datetime(2026, 1, 1, 9, 0),
        )
        await repo.add(diagnosis)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_diagnosed_by_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyVisitDiagnosisRepository(db_session)

        diagnosis = VisitDiagnosis.create(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=1,
            diagnosis_name="Orphaned attribution",
            diagnosis_type=DiagnosisType.PRIMARY,
            diagnosed_at=datetime(2026, 1, 1, 9, 0),
            diagnosed_by=uuid4(),
        )
        await repo.add(diagnosis)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestCheckConstraints:
    """`VisitDiagnosis.__post_init__` already prevents these states from
    ever existing via the domain layer — these tests target the DB
    `CHECK` constraints directly (bypassing the domain entity, the way a
    direct SQL edit would) to prove the defense-in-depth layer actually
    works, the same pattern
    `tests.integration.modules.chief_complaints.test_visit_chief_complaint_repository.TestNumericRangeCheckConstraints`
    already established."""

    async def test_sequence_number_below_one_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)

        model = VisitDiagnosisModel(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=0,
            diagnosis_name="Bad sequence",
            diagnosis_type=DiagnosisType.PRIMARY,
            diagnosed_at=datetime(2026, 1, 1, 9, 0),
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_primary_ruled_out_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, _doctor, visit = await _persist_full_chain(db_session)

        model = VisitDiagnosisModel(
            organization_id=organization.id,
            visit_id=visit.id,
            sequence_number=1,
            diagnosis_name="Bad state",
            diagnosis_type=DiagnosisType.PRIMARY,
            diagnosis_status=DiagnosisStatus.RULED_OUT,
            diagnosed_at=datetime(2026, 1, 1, 9, 0),
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
