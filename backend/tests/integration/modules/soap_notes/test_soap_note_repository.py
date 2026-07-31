"""Integration tests for `SqlAlchemySOAPNoteRepository`, including the FKs
to `organizations`/`clinical_notes`/`patients`/`patient_visits`/`doctors`
and the "at most one SOAP note per clinical note" partial unique index,
against a real PostgreSQL instance.

No `TestCheckConstraints` class here, unlike
`tests.integration.modules.clinical_notes.test_clinical_note_repository`
— `soap_notes` carries no `CHECK` constraints at all (see
`app/modules/soap_notes/infrastructure/models.py` for why "read-only when
Signed/Locked" has no database-level enforcement layer)."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.soap_notes._helpers import persist_full_chain

from app.modules.soap_notes.domain.entities import SOAPNote
from app.modules.soap_notes.infrastructure.repositories import SqlAlchemySOAPNoteRepository


class TestSOAPNoteRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemySOAPNoteRepository(db_session)

        soap_note = SOAPNote.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            chief_complaint="Persistent cough",
            history_of_present_illness="Symptoms for 3 days",
            review_of_systems="No fever, no chills",
            physical_examination="Lungs clear on auscultation",
            vital_sign_summary="BP 120/80, HR 72",
            assessment="Likely viral upper respiratory infection",
            plan="Rest and fluids, follow up in 1 week",
        )
        await repo.add(soap_note)
        await db_session.commit()

        reloaded = await repo.get_by_id(soap_note.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.clinical_note_id == clinical_note.id
        assert reloaded.patient_id == patient.id
        assert reloaded.visit_id == visit.id
        assert reloaded.doctor_id == doctor.id
        assert reloaded.chief_complaint == "Persistent cough"
        assert reloaded.history_of_present_illness == "Symptoms for 3 days"
        assert reloaded.review_of_systems == "No fever, no chills"
        assert reloaded.physical_examination == "Lungs clear on auscultation"
        assert reloaded.vital_sign_summary == "BP 120/80, HR 72"
        assert reloaded.assessment == "Likely viral upper respiratory infection"
        assert reloaded.plan == "Rest and fluids, follow up in 1 week"

    async def test_save_with_all_text_fields_null_while_drafting(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemySOAPNoteRepository(db_session)

        soap_note = SOAPNote.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
        )
        await repo.add(soap_note)
        await db_session.commit()

        reloaded = await repo.get_by_id(soap_note.id)
        assert reloaded is not None
        assert reloaded.chief_complaint is None
        assert reloaded.assessment is None
        assert reloaded.plan is None

    async def test_update_via_upsert_add_persists_changes(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemySOAPNoteRepository(db_session)

        soap_note = SOAPNote.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            assessment="Initial assessment",
        )
        await repo.add(soap_note)
        await db_session.commit()

        soap_note.update_details(assessment="Revised assessment")
        await repo.add(soap_note)
        await db_session.commit()

        reloaded = await repo.get_by_id(soap_note.id)
        assert reloaded is not None
        assert reloaded.assessment == "Revised assessment"


class TestGetByClinicalNoteId:
    async def test_returns_the_matching_soap_note(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemySOAPNoteRepository(db_session)

        soap_note = SOAPNote.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
        )
        await repo.add(soap_note)
        await db_session.commit()

        found = await repo.get_by_clinical_note_id(clinical_note.id)
        assert found is not None and found.id == soap_note.id

    async def test_returns_none_for_an_unknown_clinical_note(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemySOAPNoteRepository(db_session)
        assert await repo.get_by_clinical_note_id(uuid4()) is None


class TestOneToOneUniqueness:
    async def test_a_second_soap_note_for_the_same_clinical_note_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemySOAPNoteRepository(db_session)

        first = SOAPNote.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
        )
        await repo.add(first)
        await db_session.commit()

        second = SOAPNote.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestSOAPNoteSearch:
    """Search & Filtering module — `SqlAlchemySOAPNoteRepository.search`.

    The module's first collection-listing capability — previously only
    single-record lookup by `clinical_note_id` existed."""

    async def test_scopes_to_organization_and_filters_by_patient(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, clinical_note = await persist_full_chain(db_session)
        _org2, other_patient, other_doctor, other_visit, other_note = await persist_full_chain(
            db_session
        )
        repo = SqlAlchemySOAPNoteRepository(db_session)
        note = SOAPNote.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            assessment="Likely viral pharyngitis",
        )
        other = SOAPNote.create(
            organization_id=_org2.id,
            clinical_note_id=other_note.id,
            patient_id=other_patient.id,
            visit_id=other_visit.id,
            doctor_id=other_doctor.id,
        )
        await repo.add(note)
        await repo.add(other)
        await db_session.commit()

        results, total = await repo.search(organization_id=organization.id, patient_id=patient.id)

        assert total == 1
        assert [n.id for n in results] == [note.id]

    async def test_query_matches_free_text_fields(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemySOAPNoteRepository(db_session)
        note = SOAPNote.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            assessment="Likely viral pharyngitis",
        )
        await repo.add(note)
        await db_session.commit()

        results, total = await repo.search(organization_id=organization.id, query="pharyngitis")

        assert total == 1
        assert [n.id for n in results] == [note.id]


class TestSOAPNoteRequiresValidReferences:
    async def test_nonexistent_organization_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        _organization, patient, doctor, visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemySOAPNoteRepository(db_session)

        soap_note = SOAPNote.create(
            organization_id=uuid4(),
            clinical_note_id=clinical_note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
        )
        await repo.add(soap_note)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_clinical_note_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, _clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemySOAPNoteRepository(db_session)

        soap_note = SOAPNote.create(
            organization_id=organization.id,
            clinical_note_id=uuid4(),
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
        )
        await repo.add(soap_note)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_patient_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, doctor, visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemySOAPNoteRepository(db_session)

        soap_note = SOAPNote.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note.id,
            patient_id=uuid4(),
            visit_id=visit.id,
            doctor_id=doctor.id,
        )
        await repo.add(soap_note)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_visit_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, _visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemySOAPNoteRepository(db_session)

        soap_note = SOAPNote.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note.id,
            patient_id=patient.id,
            visit_id=uuid4(),
            doctor_id=doctor.id,
        )
        await repo.add(soap_note)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_doctor_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, _doctor, visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemySOAPNoteRepository(db_session)

        soap_note = SOAPNote.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=uuid4(),
        )
        await repo.add(soap_note)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
