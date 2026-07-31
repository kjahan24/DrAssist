"""Integration tests for `SqlAlchemyClinicalNoteRepository`, including
the FKs to `organizations`/`patients`/`patient_visits`/`doctors`, the
global `note_number` uniqueness constraint, and the signature/`locked_at`
consistency `CHECK` constraints, against a real PostgreSQL instance."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.clinical_notes._helpers import (
    persist_doctor,
    persist_organization,
    persist_patient,
    persist_visit,
)

from app.modules.clinical_notes.domain.entities import ClinicalNote
from app.modules.clinical_notes.domain.enums import ClinicalNoteStatus, ClinicalNoteType
from app.modules.clinical_notes.infrastructure.models import ClinicalNoteModel
from app.modules.clinical_notes.infrastructure.repositories import (
    SqlAlchemyClinicalNoteRepository,
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


class TestClinicalNoteRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyClinicalNoteRepository(db_session)

        note = ClinicalNote.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            note_number="CN-0001",
            note_type=ClinicalNoteType.INITIAL,
            encounter_datetime=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
            chief_complaint_summary="Persistent cough",
            history_summary="Symptoms for 3 days",
            examination_summary="Lungs clear",
            assessment_summary="Likely viral",
            plan_summary="Rest and fluids",
            ai_generated=True,
            ai_model="gemini-2.5-pro",
            ai_version="1.0",
        )
        await repo.add(note)
        await db_session.commit()

        reloaded = await repo.get_by_id(note.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.patient_id == patient.id
        assert reloaded.visit_id == visit.id
        assert reloaded.doctor_id == doctor.id
        assert reloaded.note_number == "CN-0001"
        assert reloaded.note_type is ClinicalNoteType.INITIAL
        assert reloaded.status is ClinicalNoteStatus.DRAFT
        assert reloaded.chief_complaint_summary == "Persistent cough"
        assert reloaded.history_summary == "Symptoms for 3 days"
        assert reloaded.examination_summary == "Lungs clear"
        assert reloaded.assessment_summary == "Likely viral"
        assert reloaded.plan_summary == "Rest and fluids"
        assert reloaded.ai_generated is True
        assert reloaded.ai_model == "gemini-2.5-pro"
        assert reloaded.ai_version == "1.0"
        assert reloaded.signature is None
        assert reloaded.locked_at is None

    async def test_full_lifecycle_persists(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyClinicalNoteRepository(db_session)

        note = ClinicalNote.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            note_number="CN-0002",
            note_type=ClinicalNoteType.FOLLOW_UP,
            encounter_datetime=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        await repo.add(note)
        await db_session.commit()

        note.submit_for_review()
        await repo.add(note)
        await db_session.commit()

        signed_at = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
        note.sign(signed_at=signed_at, signed_by=doctor.id)
        await repo.add(note)
        await db_session.commit()

        locked_at = datetime(2026, 1, 1, 11, 0, tzinfo=UTC)
        note.lock(locked_at=locked_at)
        await repo.add(note)
        await db_session.commit()

        reloaded = await repo.get_by_id(note.id)
        assert reloaded is not None
        assert reloaded.status is ClinicalNoteStatus.LOCKED
        assert reloaded.signature is not None
        assert reloaded.signature.signed_at == signed_at
        assert reloaded.signature.signed_by == doctor.id
        assert reloaded.locked_at == locked_at


class TestGetByNoteNumber:
    async def test_returns_the_matching_note(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyClinicalNoteRepository(db_session)

        note = ClinicalNote.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            note_number="CN-UNIQUE",
            note_type=ClinicalNoteType.INITIAL,
            encounter_datetime=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        await repo.add(note)
        await db_session.commit()

        found = await repo.get_by_note_number("CN-UNIQUE")
        assert found is not None and found.id == note.id

    async def test_returns_none_for_an_unknown_note_number(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyClinicalNoteRepository(db_session)
        assert await repo.get_by_note_number("does-not-exist") is None


class TestListByVisit:
    async def test_returns_notes_scoped_to_the_visit(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit_a = await _persist_full_chain(db_session)
        visit_b = await persist_visit(
            db_session, organization_id=organization.id, patient_id=patient.id, doctor_id=doctor.id
        )
        repo = SqlAlchemyClinicalNoteRepository(db_session)

        await repo.add(
            ClinicalNote.create(
                organization_id=organization.id,
                patient_id=patient.id,
                visit_id=visit_a.id,
                doctor_id=doctor.id,
                note_number="CN-A",
                note_type=ClinicalNoteType.INITIAL,
                encounter_datetime=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
            )
        )
        await repo.add(
            ClinicalNote.create(
                organization_id=organization.id,
                patient_id=patient.id,
                visit_id=visit_b.id,
                doctor_id=doctor.id,
                note_number="CN-B",
                note_type=ClinicalNoteType.FOLLOW_UP,
                encounter_datetime=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
            )
        )
        await db_session.commit()

        notes = await repo.list_by_visit(visit_a.id)
        assert [n.note_number for n in notes] == ["CN-A"]


class TestListByPatient:
    async def test_returns_notes_scoped_to_the_patient_across_visits(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit_a = await _persist_full_chain(db_session)
        visit_b = await persist_visit(
            db_session, organization_id=organization.id, patient_id=patient.id, doctor_id=doctor.id
        )
        other_patient = await persist_patient(db_session, organization_id=organization.id)
        repo = SqlAlchemyClinicalNoteRepository(db_session)

        await repo.add(
            ClinicalNote.create(
                organization_id=organization.id,
                patient_id=patient.id,
                visit_id=visit_a.id,
                doctor_id=doctor.id,
                note_number="CN-PAT-A",
                note_type=ClinicalNoteType.INITIAL,
                encounter_datetime=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
            )
        )
        await repo.add(
            ClinicalNote.create(
                organization_id=organization.id,
                patient_id=patient.id,
                visit_id=visit_b.id,
                doctor_id=doctor.id,
                note_number="CN-PAT-B",
                note_type=ClinicalNoteType.FOLLOW_UP,
                encounter_datetime=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
            )
        )
        await repo.add(
            ClinicalNote.create(
                organization_id=organization.id,
                patient_id=other_patient.id,
                visit_id=visit_a.id,
                doctor_id=doctor.id,
                note_number="CN-PAT-OTHER",
                note_type=ClinicalNoteType.INITIAL,
                encounter_datetime=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
            )
        )
        await db_session.commit()

        notes = await repo.list_by_patient(patient.id)
        assert {n.note_number for n in notes} == {"CN-PAT-A", "CN-PAT-B"}


class TestNoteNumberUniqueness:
    async def test_duplicate_note_number_across_different_visits_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit_a = await _persist_full_chain(db_session)
        visit_b = await persist_visit(
            db_session, organization_id=organization.id, patient_id=patient.id, doctor_id=doctor.id
        )
        repo = SqlAlchemyClinicalNoteRepository(db_session)
        shared_note_number = "CN-SHARED"

        first = ClinicalNote.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit_a.id,
            doctor_id=doctor.id,
            note_number=shared_note_number,
            note_type=ClinicalNoteType.INITIAL,
            encounter_datetime=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        await repo.add(first)
        await db_session.commit()

        second = ClinicalNote.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit_b.id,
            doctor_id=doctor.id,
            note_number=shared_note_number,
            note_type=ClinicalNoteType.FOLLOW_UP,
            encounter_datetime=datetime(2026, 1, 1, 9, 5, tzinfo=UTC),
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestClinicalNoteSearch:
    """Search & Filtering module — `SqlAlchemyClinicalNoteRepository.search`."""

    async def test_scopes_to_organization_and_filters_by_visit(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit = await _persist_full_chain(db_session)
        _org2, other_patient, other_doctor, other_visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyClinicalNoteRepository(db_session)
        note = ClinicalNote.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            note_number=f"CN-{uuid4().hex[:12].upper()}",
            note_type=ClinicalNoteType.INITIAL,
            encounter_datetime=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
            assessment_summary="Likely viral pharyngitis",
        )
        other = ClinicalNote.create(
            organization_id=_org2.id,
            patient_id=other_patient.id,
            visit_id=other_visit.id,
            doctor_id=other_doctor.id,
            note_number=f"CN-{uuid4().hex[:12].upper()}",
            note_type=ClinicalNoteType.INITIAL,
            encounter_datetime=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        await repo.add(note)
        await repo.add(other)
        await db_session.commit()

        results, total = await repo.search(organization_id=organization.id, visit_id=visit.id)

        assert total == 1
        assert [n.id for n in results] == [note.id]

    async def test_query_matches_assessment_summary_full_text(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyClinicalNoteRepository(db_session)
        note = ClinicalNote.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            note_number=f"CN-{uuid4().hex[:12].upper()}",
            note_type=ClinicalNoteType.INITIAL,
            encounter_datetime=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
            assessment_summary="Likely viral pharyngitis",
        )
        await repo.add(note)
        await db_session.commit()

        results, total = await repo.search(organization_id=organization.id, query="pharyngitis")

        assert total == 1
        assert [n.id for n in results] == [note.id]

    async def test_status_and_encounter_datetime_range_filters(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyClinicalNoteRepository(db_session)
        draft = ClinicalNote.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            note_number=f"CN-{uuid4().hex[:12].upper()}",
            note_type=ClinicalNoteType.INITIAL,
            encounter_datetime=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        reviewed = ClinicalNote.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            note_number=f"CN-{uuid4().hex[:12].upper()}",
            note_type=ClinicalNoteType.INITIAL,
            encounter_datetime=datetime(2026, 6, 1, 9, 0, tzinfo=UTC),
        )
        reviewed.submit_for_review()
        await repo.add(draft)
        await repo.add(reviewed)
        await db_session.commit()

        results, total = await repo.search(
            organization_id=organization.id,
            statuses=[ClinicalNoteStatus.IN_REVIEW],
            encounter_from=datetime(2026, 3, 1, tzinfo=UTC),
        )

        assert total == 1
        assert [n.id for n in results] == [reviewed.id]


class TestClinicalNoteRequiresValidReferences:
    async def test_nonexistent_patient_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyClinicalNoteRepository(db_session)

        note = ClinicalNote.create(
            organization_id=organization.id,
            patient_id=uuid4(),
            visit_id=visit.id,
            doctor_id=doctor.id,
            note_number="CN-ORPHAN-PATIENT",
            note_type=ClinicalNoteType.INITIAL,
            encounter_datetime=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        await repo.add(note)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_visit_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, _visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyClinicalNoteRepository(db_session)

        note = ClinicalNote.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=uuid4(),
            doctor_id=doctor.id,
            note_number="CN-ORPHAN-VISIT",
            note_type=ClinicalNoteType.INITIAL,
            encounter_datetime=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        await repo.add(note)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_doctor_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, _doctor, visit = await _persist_full_chain(db_session)
        repo = SqlAlchemyClinicalNoteRepository(db_session)

        note = ClinicalNote.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=uuid4(),
            note_number="CN-ORPHAN-DOCTOR",
            note_type=ClinicalNoteType.INITIAL,
            encounter_datetime=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        await repo.add(note)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestCheckConstraints:
    """`ClinicalNote.__post_init__` already prevents these states from
    ever existing via the domain layer — these tests target the DB
    `CHECK` constraints directly (bypassing the domain entity, the way a
    direct SQL edit would) to prove the defense-in-depth layer actually
    works, the same pattern
    `tests.integration.modules.diagnosis.test_visit_diagnosis_repository.TestCheckConstraints`
    already established."""

    async def test_signed_without_signature_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit = await _persist_full_chain(db_session)

        model = ClinicalNoteModel(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            note_number="CN-BAD-SIGNED",
            note_type=ClinicalNoteType.INITIAL,
            status=ClinicalNoteStatus.SIGNED,
            encounter_datetime=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_draft_with_signature_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit = await _persist_full_chain(db_session)

        model = ClinicalNoteModel(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            note_number="CN-BAD-DRAFT",
            note_type=ClinicalNoteType.INITIAL,
            status=ClinicalNoteStatus.DRAFT,
            encounter_datetime=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
            signed_at=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
            signed_by=doctor.id,
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_locked_without_locked_at_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit = await _persist_full_chain(db_session)

        model = ClinicalNoteModel(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            note_number="CN-BAD-LOCKED",
            note_type=ClinicalNoteType.INITIAL,
            status=ClinicalNoteStatus.LOCKED,
            encounter_datetime=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
            signed_at=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
            signed_by=doctor.id,
            locked_at=None,
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_signed_with_locked_at_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit = await _persist_full_chain(db_session)

        model = ClinicalNoteModel(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            note_number="CN-BAD-LOCKED-AT",
            note_type=ClinicalNoteType.INITIAL,
            status=ClinicalNoteStatus.SIGNED,
            encounter_datetime=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
            signed_at=datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
            signed_by=doctor.id,
            locked_at=datetime(2026, 1, 1, 11, 0, tzinfo=UTC),
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
