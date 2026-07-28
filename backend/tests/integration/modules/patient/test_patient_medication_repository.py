"""Integration tests for `SqlAlchemyPatientMedicationRepository`,
including the FKs to `patients`/`doctors` and the two `CHECK` constraints,
against a real PostgreSQL instance."""

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.patient._helpers import persist_doctor, persist_patient

from app.modules.patient.domain.entities import PatientMedication
from app.modules.patient.domain.enums import AdherenceStatus, RouteOfAdministration
from app.modules.patient.infrastructure.models import PatientMedicationModel
from app.modules.patient.infrastructure.repositories import SqlAlchemyPatientMedicationRepository


class TestPatientMedicationRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        patient = await persist_patient(db_session)
        doctor = await persist_doctor(db_session, organization_id=patient.organization_id)
        repo = SqlAlchemyPatientMedicationRepository(db_session)

        medication = PatientMedication.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            medication_name="Amoxicillin",
            dosage="500",
            route=RouteOfAdministration.ORAL,
            start_date=date(2026, 1, 1),
            prescribed_by=doctor.id,
            generic_name="Amoxicillin trihydrate",
            brand_name="Amoxil",
            dosage_unit="mg",
            frequency="three times daily",
            indication="Sinus infection",
            instructions="Take with food",
            notes="No known issues",
        )
        await repo.add(medication)
        await db_session.commit()

        reloaded = await repo.get_by_id(medication.id)
        assert reloaded is not None
        assert reloaded.patient_id == patient.id
        assert reloaded.prescribed_by == doctor.id
        assert reloaded.medication_name == "Amoxicillin"
        assert reloaded.generic_name == "Amoxicillin trihydrate"
        assert reloaded.brand_name == "Amoxil"
        assert reloaded.dosage == "500"
        assert reloaded.dosage_unit == "mg"
        assert reloaded.route is RouteOfAdministration.ORAL
        assert reloaded.frequency == "three times daily"
        assert reloaded.indication == "Sinus infection"
        assert reloaded.is_current is True
        assert reloaded.adherence_status is AdherenceStatus.TAKING
        assert reloaded.instructions == "Take with food"
        assert reloaded.notes == "No known issues"

    async def test_discontinue_persists(self, db_session: AsyncSession) -> None:
        patient = await persist_patient(db_session)
        repo = SqlAlchemyPatientMedicationRepository(db_session)

        medication = PatientMedication.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            medication_name="Ibuprofen",
            dosage="200",
            route=RouteOfAdministration.ORAL,
            start_date=date(2026, 1, 1),
        )
        await repo.add(medication)
        await db_session.commit()

        medication.discontinue(end_date=date(2026, 1, 10))
        await repo.add(medication)
        await db_session.commit()

        reloaded = await repo.get_by_id(medication.id)
        assert reloaded is not None
        assert reloaded.is_current is False
        assert reloaded.adherence_status is AdherenceStatus.STOPPED
        assert reloaded.end_date == date(2026, 1, 10)

    async def test_list_by_patient_scopes_to_a_single_patient(
        self, db_session: AsyncSession
    ) -> None:
        patient_a = await persist_patient(db_session)
        patient_b = await persist_patient(db_session)
        repo = SqlAlchemyPatientMedicationRepository(db_session)

        medication_a = PatientMedication.create(
            organization_id=patient_a.organization_id,
            patient_id=patient_a.id,
            medication_name="Amoxicillin",
            dosage="500",
            route=RouteOfAdministration.ORAL,
            start_date=date(2026, 1, 1),
        )
        medication_b = PatientMedication.create(
            organization_id=patient_b.organization_id,
            patient_id=patient_b.id,
            medication_name="Ibuprofen",
            dosage="200",
            route=RouteOfAdministration.ORAL,
            start_date=date(2026, 1, 1),
        )
        await repo.add(medication_a)
        await repo.add(medication_b)
        await db_session.commit()

        medications_for_a = await repo.list_by_patient(patient_a.id)
        assert [m.id for m in medications_for_a] == [medication_a.id]

    async def test_multiple_medications_for_the_same_patient_are_allowed(
        self, db_session: AsyncSession
    ) -> None:
        patient = await persist_patient(db_session)
        repo = SqlAlchemyPatientMedicationRepository(db_session)

        first = PatientMedication.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            medication_name="Amoxicillin",
            dosage="500",
            route=RouteOfAdministration.ORAL,
            start_date=date(2026, 1, 1),
        )
        second = PatientMedication.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            medication_name="Amoxicillin",
            dosage="250",
            route=RouteOfAdministration.ORAL,
            start_date=date(2026, 3, 1),
        )
        await repo.add(first)
        await repo.add(second)
        await db_session.commit()

        medications = await repo.list_by_patient(patient.id)
        assert {m.id for m in medications} == {first.id, second.id}


class TestPatientMedicationRequiresValidReferences:
    async def test_nonexistent_patient_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization_id = (await persist_patient(db_session)).organization_id
        repo = SqlAlchemyPatientMedicationRepository(db_session)

        medication = PatientMedication.create(
            organization_id=organization_id,
            patient_id=uuid4(),
            medication_name="Amoxicillin",
            dosage="500",
            route=RouteOfAdministration.ORAL,
            start_date=date(2026, 1, 1),
        )
        await repo.add(medication)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_prescribing_doctor_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        patient = await persist_patient(db_session)
        repo = SqlAlchemyPatientMedicationRepository(db_session)

        medication = PatientMedication.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            medication_name="Amoxicillin",
            dosage="500",
            route=RouteOfAdministration.ORAL,
            start_date=date(2026, 1, 1),
            prescribed_by=uuid4(),
        )
        await repo.add(medication)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestDateRangeCheckConstraint:
    async def test_an_end_date_before_start_date_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        """`PatientMedication.__post_init__` already prevents this state
        from ever existing via the domain layer — this test targets the DB
        `CHECK` constraint directly (bypassing the domain entity, the way
        a direct SQL edit would) to prove the defense-in-depth layer
        actually works."""
        patient = await persist_patient(db_session)

        model = PatientMedicationModel(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            medication_name="Amoxicillin",
            dosage="500",
            route=RouteOfAdministration.ORAL,
            start_date=date(2026, 1, 10),
            end_date=date(2026, 1, 1),
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestCompletedRequiresEndDateCheckConstraint:
    async def test_not_current_and_completed_without_end_date_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        """Same defense-in-depth rationale as
        `TestDateRangeCheckConstraint` above, for the "if is_current is
        false and treatment is completed, end_date is required" rule."""
        patient = await persist_patient(db_session)

        model = PatientMedicationModel(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            medication_name="Amoxicillin",
            dosage="500",
            route=RouteOfAdministration.ORAL,
            start_date=date(2026, 1, 1),
            is_current=False,
            adherence_status=AdherenceStatus.COMPLETED,
            end_date=None,
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
