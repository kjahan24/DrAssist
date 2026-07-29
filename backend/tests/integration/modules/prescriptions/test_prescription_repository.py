"""Integration tests for `SqlAlchemyPrescriptionRepository`, including the
FKs to `organizations`/`clinical_notes`/`patients`/`patient_visits`/
`doctors`, the "at most one prescription per clinical note" partial
unique index, and the "prescription_number is globally unique" partial
unique index, against a real PostgreSQL instance.

No `TestCheckConstraints` class here, matching
`tests.integration.modules.soap_notes.test_soap_note_repository` — like
`soap_notes`, `prescriptions` carries no `CHECK` constraints at all (see
`app/modules/prescriptions/infrastructure/models.py` for why "a Final
Prescription must contain at least one Prescription Item" has no
database-level enforcement layer)."""

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.prescriptions._helpers import (
    persist_clinical_note,
    persist_full_chain,
    persist_visit,
)

from app.modules.prescriptions.domain.entities import Prescription
from app.modules.prescriptions.domain.enums import PrescriptionStatus
from app.modules.prescriptions.infrastructure.repositories import SqlAlchemyPrescriptionRepository


class TestPrescriptionRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemyPrescriptionRepository(db_session)

        prescription = Prescription.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            prescription_number="RX-0001",
            prescription_date=date(2026, 1, 1),
            notes="Take with food",
        )
        await repo.add(prescription)
        await db_session.commit()

        reloaded = await repo.get_by_id(prescription.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.clinical_note_id == clinical_note.id
        assert reloaded.patient_id == patient.id
        assert reloaded.visit_id == visit.id
        assert reloaded.doctor_id == doctor.id
        assert reloaded.prescription_number == "RX-0001"
        assert reloaded.prescription_date == date(2026, 1, 1)
        assert reloaded.status is PrescriptionStatus.DRAFT
        assert reloaded.notes == "Take with food"

    async def test_finalize_persists_status(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemyPrescriptionRepository(db_session)

        prescription = Prescription.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            prescription_number="RX-0002",
            prescription_date=date(2026, 1, 1),
        )
        await repo.add(prescription)
        await db_session.commit()

        prescription.finalize()
        await repo.add(prescription)
        await db_session.commit()

        reloaded = await repo.get_by_id(prescription.id)
        assert reloaded is not None
        assert reloaded.status is PrescriptionStatus.FINAL


class TestGetByClinicalNoteId:
    async def test_returns_the_matching_prescription(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemyPrescriptionRepository(db_session)

        prescription = Prescription.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            prescription_number="RX-0003",
            prescription_date=date(2026, 1, 1),
        )
        await repo.add(prescription)
        await db_session.commit()

        found = await repo.get_by_clinical_note_id(clinical_note.id)
        assert found is not None and found.id == prescription.id

    async def test_returns_none_for_an_unknown_clinical_note(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyPrescriptionRepository(db_session)
        assert await repo.get_by_clinical_note_id(uuid4()) is None


class TestGetByPrescriptionNumber:
    async def test_returns_the_matching_prescription(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemyPrescriptionRepository(db_session)

        prescription = Prescription.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            prescription_number="RX-UNIQUE",
            prescription_date=date(2026, 1, 1),
        )
        await repo.add(prescription)
        await db_session.commit()

        found = await repo.get_by_prescription_number("RX-UNIQUE")
        assert found is not None and found.id == prescription.id

    async def test_returns_none_for_an_unknown_number(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyPrescriptionRepository(db_session)
        assert await repo.get_by_prescription_number("does-not-exist") is None


class TestListByPatient:
    async def test_returns_prescriptions_scoped_to_the_patient_across_visits(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit_a, clinical_note_a = await persist_full_chain(
            db_session
        )
        visit_b = await persist_visit(
            db_session, organization_id=organization.id, patient_id=patient.id, doctor_id=doctor.id
        )
        clinical_note_b = await persist_clinical_note(
            db_session,
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit_b.id,
            doctor_id=doctor.id,
        )
        (
            other_patient_org,
            other_patient,
            other_doctor,
            other_visit,
            other_note,
        ) = await persist_full_chain(db_session)
        repo = SqlAlchemyPrescriptionRepository(db_session)

        await repo.add(
            Prescription.create(
                organization_id=organization.id,
                clinical_note_id=clinical_note_a.id,
                patient_id=patient.id,
                visit_id=visit_a.id,
                doctor_id=doctor.id,
                prescription_number="RX-PAT-A",
                prescription_date=date(2026, 1, 1),
            )
        )
        await repo.add(
            Prescription.create(
                organization_id=organization.id,
                clinical_note_id=clinical_note_b.id,
                patient_id=patient.id,
                visit_id=visit_b.id,
                doctor_id=doctor.id,
                prescription_number="RX-PAT-B",
                prescription_date=date(2026, 1, 1),
            )
        )
        await repo.add(
            Prescription.create(
                organization_id=other_patient_org.id,
                clinical_note_id=other_note.id,
                patient_id=other_patient.id,
                visit_id=other_visit.id,
                doctor_id=other_doctor.id,
                prescription_number="RX-PAT-OTHER",
                prescription_date=date(2026, 1, 1),
            )
        )
        await db_session.commit()

        prescriptions = await repo.list_by_patient(patient.id)
        assert {p.prescription_number for p in prescriptions} == {"RX-PAT-A", "RX-PAT-B"}


class TestOneToOneUniqueness:
    async def test_a_second_prescription_for_the_same_clinical_note_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemyPrescriptionRepository(db_session)

        first = Prescription.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            prescription_number="RX-FIRST",
            prescription_date=date(2026, 1, 1),
        )
        await repo.add(first)
        await db_session.commit()

        second = Prescription.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            prescription_number="RX-SECOND",
            prescription_date=date(2026, 1, 1),
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestPrescriptionNumberUniqueness:
    async def test_duplicate_prescription_number_across_different_notes_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit_a, clinical_note_a = await persist_full_chain(
            db_session
        )
        visit_b = await persist_visit(
            db_session, organization_id=organization.id, patient_id=patient.id, doctor_id=doctor.id
        )
        clinical_note_b = await persist_clinical_note(
            db_session,
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit_b.id,
            doctor_id=doctor.id,
        )
        repo = SqlAlchemyPrescriptionRepository(db_session)
        shared_number = "RX-SHARED"

        first = Prescription.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note_a.id,
            patient_id=patient.id,
            visit_id=visit_a.id,
            doctor_id=doctor.id,
            prescription_number=shared_number,
            prescription_date=date(2026, 1, 1),
        )
        await repo.add(first)
        await db_session.commit()

        second = Prescription.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note_b.id,
            patient_id=patient.id,
            visit_id=visit_b.id,
            doctor_id=doctor.id,
            prescription_number=shared_number,
            prescription_date=date(2026, 1, 5),
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestPrescriptionRequiresValidReferences:
    async def test_nonexistent_organization_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        _organization, patient, doctor, visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemyPrescriptionRepository(db_session)

        prescription = Prescription.create(
            organization_id=uuid4(),
            clinical_note_id=clinical_note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            prescription_number="RX-ORPHAN-ORG",
            prescription_date=date(2026, 1, 1),
        )
        await repo.add(prescription)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_clinical_note_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, _clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemyPrescriptionRepository(db_session)

        prescription = Prescription.create(
            organization_id=organization.id,
            clinical_note_id=uuid4(),
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            prescription_number="RX-ORPHAN-NOTE",
            prescription_date=date(2026, 1, 1),
        )
        await repo.add(prescription)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_patient_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, doctor, visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemyPrescriptionRepository(db_session)

        prescription = Prescription.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note.id,
            patient_id=uuid4(),
            visit_id=visit.id,
            doctor_id=doctor.id,
            prescription_number="RX-ORPHAN-PATIENT",
            prescription_date=date(2026, 1, 1),
        )
        await repo.add(prescription)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_visit_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, _visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemyPrescriptionRepository(db_session)

        prescription = Prescription.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note.id,
            patient_id=patient.id,
            visit_id=uuid4(),
            doctor_id=doctor.id,
            prescription_number="RX-ORPHAN-VISIT",
            prescription_date=date(2026, 1, 1),
        )
        await repo.add(prescription)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_doctor_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, _doctor, visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemyPrescriptionRepository(db_session)

        prescription = Prescription.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=uuid4(),
            prescription_number="RX-ORPHAN-DOCTOR",
            prescription_date=date(2026, 1, 1),
        )
        await repo.add(prescription)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
