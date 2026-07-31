"""Integration tests for `SqlAlchemyPatientHistoryRepository`, including
the FKs to `organizations`/`patients`/`patient_visits`/`doctor_reviews`
and the "duplicate history records for the same source are prohibited"
partial unique index on `(reference_type, reference_id)`, against a real
PostgreSQL instance.
"""

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.patient_history._helpers import persist_full_chain

from app.modules.patient_history.domain.entities import PatientHistory
from app.modules.patient_history.domain.enums import HistoryType, ReferenceType
from app.modules.patient_history.infrastructure.repositories import (
    SqlAlchemyPatientHistoryRepository,
)


class TestPatientHistoryRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, note, review = await persist_full_chain(db_session)
        repo = SqlAlchemyPatientHistoryRepository(db_session)

        history = PatientHistory.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_review_id=review.id,
            history_type=HistoryType.CLINICAL_NOTE,
            reference_type=ReferenceType.CLINICAL_NOTE,
            reference_id=note.id,
            encounter_date=date(2026, 1, 1),
            summary="Initial encounter: community-acquired pneumonia",
        )
        await repo.add(history)
        await db_session.commit()

        reloaded = await repo.get_by_id(history.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.patient_id == patient.id
        assert reloaded.visit_id == visit.id
        assert reloaded.doctor_review_id == review.id
        assert reloaded.history_type is HistoryType.CLINICAL_NOTE
        assert reloaded.reference_type is ReferenceType.CLINICAL_NOTE
        assert reloaded.reference_id == note.id
        assert reloaded.encounter_date == date(2026, 1, 1)
        assert reloaded.summary == "Initial encounter: community-acquired pneumonia"
        assert reloaded.created_from_review is True


class TestGetByReference:
    async def test_returns_the_matching_record(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, note, review = await persist_full_chain(db_session)
        repo = SqlAlchemyPatientHistoryRepository(db_session)

        history = PatientHistory.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_review_id=review.id,
            history_type=HistoryType.DIAGNOSIS,
            reference_type=ReferenceType.ICD10,
            reference_id=uuid4(),
            encounter_date=date(2026, 1, 1),
            summary="ICD-10 coded diagnosis",
        )
        await repo.add(history)
        await db_session.commit()

        found = await repo.get_by_reference(ReferenceType.ICD10, history.reference_id)
        assert found is not None and found.id == history.id

    async def test_returns_none_for_an_unmatched_reference(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyPatientHistoryRepository(db_session)
        assert await repo.get_by_reference(ReferenceType.ICD10, uuid4()) is None


class TestListByPatient:
    async def test_returns_history_ordered_by_encounter_date(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, note, review = await persist_full_chain(db_session)
        repo = SqlAlchemyPatientHistoryRepository(db_session)

        await repo.add(
            PatientHistory.create(
                organization_id=organization.id,
                patient_id=patient.id,
                visit_id=visit.id,
                doctor_review_id=review.id,
                history_type=HistoryType.LAB,
                reference_type=ReferenceType.LAB_RESULT,
                reference_id=uuid4(),
                encounter_date=date(2026, 2, 1),
                summary="Second, later record",
            )
        )
        await repo.add(
            PatientHistory.create(
                organization_id=organization.id,
                patient_id=patient.id,
                visit_id=visit.id,
                doctor_review_id=review.id,
                history_type=HistoryType.CLINICAL_NOTE,
                reference_type=ReferenceType.CLINICAL_NOTE,
                reference_id=note.id,
                encounter_date=date(2026, 1, 1),
                summary="First, earlier record",
            )
        )
        await db_session.commit()

        history = await repo.list_by_patient(patient.id)
        assert [h.summary for h in history] == ["First, earlier record", "Second, later record"]

    async def test_returns_empty_list_for_a_patient_without_history(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyPatientHistoryRepository(db_session)
        assert await repo.list_by_patient(uuid4()) == []


class TestListByVisit:
    async def test_returns_history_scoped_to_the_visit(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, note, review = await persist_full_chain(db_session)
        (
            _org2,
            other_patient,
            other_doctor,
            other_visit,
            other_note,
            other_review,
        ) = await persist_full_chain(db_session)
        repo = SqlAlchemyPatientHistoryRepository(db_session)

        await repo.add(
            PatientHistory.create(
                organization_id=organization.id,
                patient_id=patient.id,
                visit_id=visit.id,
                doctor_review_id=review.id,
                history_type=HistoryType.CLINICAL_NOTE,
                reference_type=ReferenceType.CLINICAL_NOTE,
                reference_id=note.id,
                encounter_date=date(2026, 1, 1),
                summary="For our visit",
            )
        )
        await repo.add(
            PatientHistory.create(
                organization_id=_org2.id,
                patient_id=other_patient.id,
                visit_id=other_visit.id,
                doctor_review_id=other_review.id,
                history_type=HistoryType.CLINICAL_NOTE,
                reference_type=ReferenceType.CLINICAL_NOTE,
                reference_id=other_note.id,
                encounter_date=date(2026, 1, 1),
                summary="For other visit",
            )
        )
        await db_session.commit()

        history = await repo.list_by_visit(visit.id)
        assert [h.summary for h in history] == ["For our visit"]

    async def test_returns_empty_list_for_a_visit_without_history(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyPatientHistoryRepository(db_session)
        assert await repo.list_by_visit(uuid4()) == []


class TestPatientHistorySearch:
    """Search & Filtering module — `SqlAlchemyPatientHistoryRepository.search`."""

    async def test_scopes_to_organization_and_filters_by_patient(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, note, review = await persist_full_chain(db_session)
        (
            _org2,
            other_patient,
            other_doctor,
            other_visit,
            other_note,
            other_review,
        ) = await persist_full_chain(db_session)
        repo = SqlAlchemyPatientHistoryRepository(db_session)
        history = PatientHistory.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_review_id=review.id,
            history_type=HistoryType.CLINICAL_NOTE,
            reference_type=ReferenceType.CLINICAL_NOTE,
            reference_id=uuid4(),
            encounter_date=date(2026, 1, 1),
            summary="Community-acquired pneumonia follow-up",
        )
        other = PatientHistory.create(
            organization_id=_org2.id,
            patient_id=other_patient.id,
            visit_id=other_visit.id,
            doctor_review_id=other_review.id,
            history_type=HistoryType.CLINICAL_NOTE,
            reference_type=ReferenceType.CLINICAL_NOTE,
            reference_id=uuid4(),
            encounter_date=date(2026, 1, 1),
            summary="Unrelated organization's history entry",
        )
        await repo.add(history)
        await repo.add(other)
        await db_session.commit()

        results, total = await repo.search(organization_id=organization.id, patient_id=patient.id)

        assert total == 1
        assert [h.id for h in results] == [history.id]

    async def test_query_matches_summary_full_text(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, note, review = await persist_full_chain(db_session)
        repo = SqlAlchemyPatientHistoryRepository(db_session)
        history = PatientHistory.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_review_id=review.id,
            history_type=HistoryType.CLINICAL_NOTE,
            reference_type=ReferenceType.CLINICAL_NOTE,
            reference_id=uuid4(),
            encounter_date=date(2026, 1, 1),
            summary="Community-acquired pneumonia follow-up",
        )
        await repo.add(history)
        await db_session.commit()

        results, total = await repo.search(organization_id=organization.id, query="pneumonia")

        assert total == 1
        assert [h.id for h in results] == [history.id]

    async def test_history_type_reference_type_and_encounter_date_filters(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, note, review = await persist_full_chain(db_session)
        repo = SqlAlchemyPatientHistoryRepository(db_session)
        reference_id = uuid4()
        history = PatientHistory.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_review_id=review.id,
            history_type=HistoryType.CLINICAL_NOTE,
            reference_type=ReferenceType.CLINICAL_NOTE,
            reference_id=reference_id,
            encounter_date=date(2026, 6, 1),
            summary="Follow-up visit",
        )
        other_type = PatientHistory.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_review_id=review.id,
            history_type=HistoryType.LAB,
            reference_type=ReferenceType.LAB_RESULT,
            reference_id=uuid4(),
            encounter_date=date(2026, 6, 1),
            summary="Lab result recorded",
        )
        await repo.add(history)
        await repo.add(other_type)
        await db_session.commit()

        by_type, type_total = await repo.search(
            organization_id=organization.id, history_types=[HistoryType.CLINICAL_NOTE]
        )
        by_reference, reference_total = await repo.search(
            organization_id=organization.id,
            reference_types=[ReferenceType.CLINICAL_NOTE],
            reference_id=reference_id,
        )
        by_date, date_total = await repo.search(
            organization_id=organization.id, encounter_date_from=date(2026, 3, 1)
        )

        assert type_total == 1
        assert [h.id for h in by_type] == [history.id]
        assert reference_total == 1
        assert [h.id for h in by_reference] == [history.id]
        assert date_total == 2


class TestDuplicateReferenceUniqueness:
    async def test_duplicate_reference_type_and_id_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, note, review = await persist_full_chain(db_session)
        repo = SqlAlchemyPatientHistoryRepository(db_session)
        reference_id = uuid4()

        first = PatientHistory.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_review_id=review.id,
            history_type=HistoryType.DIAGNOSIS,
            reference_type=ReferenceType.ICD10,
            reference_id=reference_id,
            encounter_date=date(2026, 1, 1),
            summary="First",
        )
        await repo.add(first)
        await db_session.commit()

        second = PatientHistory.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_review_id=review.id,
            history_type=HistoryType.DIAGNOSIS,
            reference_type=ReferenceType.ICD10,
            reference_id=reference_id,
            encounter_date=date(2026, 1, 1),
            summary="Duplicate",
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_same_reference_id_with_a_different_reference_type_is_allowed(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, note, review = await persist_full_chain(db_session)
        repo = SqlAlchemyPatientHistoryRepository(db_session)
        shared_id = uuid4()

        await repo.add(
            PatientHistory.create(
                organization_id=organization.id,
                patient_id=patient.id,
                visit_id=visit.id,
                doctor_review_id=review.id,
                history_type=HistoryType.DIAGNOSIS,
                reference_type=ReferenceType.ICD10,
                reference_id=shared_id,
                encounter_date=date(2026, 1, 1),
                summary="ICD-10 record",
            )
        )
        await db_session.commit()

        await repo.add(
            PatientHistory.create(
                organization_id=organization.id,
                patient_id=patient.id,
                visit_id=visit.id,
                doctor_review_id=review.id,
                history_type=HistoryType.DIAGNOSIS,
                reference_type=ReferenceType.DIFFERENTIAL_DIAGNOSIS,
                reference_id=shared_id,
                encounter_date=date(2026, 1, 1),
                summary="Differential diagnosis record",
            )
        )
        await db_session.commit()

        history = await repo.list_by_patient(patient.id)
        assert len(history) == 2


class TestPatientHistoryRequiresValidReferences:
    async def test_nonexistent_organization_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        _organization, patient, doctor, visit, note, review = await persist_full_chain(db_session)
        repo = SqlAlchemyPatientHistoryRepository(db_session)

        history = PatientHistory.create(
            organization_id=uuid4(),
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_review_id=review.id,
            history_type=HistoryType.CLINICAL_NOTE,
            reference_type=ReferenceType.CLINICAL_NOTE,
            reference_id=note.id,
            encounter_date=date(2026, 1, 1),
            summary="Orphan org",
        )
        await repo.add(history)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_patient_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, doctor, visit, note, review = await persist_full_chain(db_session)
        repo = SqlAlchemyPatientHistoryRepository(db_session)

        history = PatientHistory.create(
            organization_id=organization.id,
            patient_id=uuid4(),
            visit_id=visit.id,
            doctor_review_id=review.id,
            history_type=HistoryType.CLINICAL_NOTE,
            reference_type=ReferenceType.CLINICAL_NOTE,
            reference_id=note.id,
            encounter_date=date(2026, 1, 1),
            summary="Orphan patient",
        )
        await repo.add(history)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_visit_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, _visit, note, review = await persist_full_chain(db_session)
        repo = SqlAlchemyPatientHistoryRepository(db_session)

        history = PatientHistory.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=uuid4(),
            doctor_review_id=review.id,
            history_type=HistoryType.CLINICAL_NOTE,
            reference_type=ReferenceType.CLINICAL_NOTE,
            reference_id=note.id,
            encounter_date=date(2026, 1, 1),
            summary="Orphan visit",
        )
        await repo.add(history)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_doctor_review_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, note, _review = await persist_full_chain(db_session)
        repo = SqlAlchemyPatientHistoryRepository(db_session)

        history = PatientHistory.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_review_id=uuid4(),
            history_type=HistoryType.CLINICAL_NOTE,
            reference_type=ReferenceType.CLINICAL_NOTE,
            reference_id=note.id,
            encounter_date=date(2026, 1, 1),
            summary="Orphan doctor review",
        )
        await repo.add(history)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
