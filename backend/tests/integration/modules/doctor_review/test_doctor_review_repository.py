"""Integration tests for `SqlAlchemyDoctorReviewRepository`, including
the FKs to `organizations`/`patients`/`patient_visits`/`doctors`/
`clinical_notes` and the "zero or one Doctor Review per Clinical Note"
partial unique index, against a real PostgreSQL instance.
"""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.doctor_review._helpers import persist_full_chain

from app.modules.doctor_review.domain.entities import DoctorReview
from app.modules.doctor_review.domain.enums import ReviewStatus
from app.modules.doctor_review.infrastructure.repositories import (
    SqlAlchemyDoctorReviewRepository,
)


class TestDoctorReviewRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyDoctorReviewRepository(db_session)

        review = DoctorReview.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            clinical_note_id=note.id,
            review_comment="Initial review",
            approved_clinical_note=True,
        )
        await repo.add(review)
        await db_session.commit()

        reloaded = await repo.get_by_id(review.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.patient_id == patient.id
        assert reloaded.visit_id == visit.id
        assert reloaded.doctor_id == doctor.id
        assert reloaded.clinical_note_id == note.id
        assert reloaded.review_status is ReviewStatus.PENDING
        assert reloaded.review_comment == "Initial review"
        assert reloaded.reviewed_at is None
        assert reloaded.approved_clinical_note is True
        assert reloaded.approved_soap_note is False

    async def test_full_approve_workflow_persists(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyDoctorReviewRepository(db_session)

        review = DoctorReview.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            clinical_note_id=note.id,
        )
        await repo.add(review)
        await db_session.commit()

        review.approve()
        await repo.add(review)
        await db_session.commit()

        reloaded = await repo.get_by_id(review.id)
        assert reloaded is not None
        assert reloaded.review_status is ReviewStatus.APPROVED
        assert reloaded.reviewed_at is not None

    async def test_return_for_revision_then_reject_workflow_persists(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyDoctorReviewRepository(db_session)

        review = DoctorReview.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            clinical_note_id=note.id,
        )
        await repo.add(review)
        await db_session.commit()

        review.return_for_revision()
        await repo.add(review)
        await db_session.commit()

        review.reject()
        await repo.add(review)
        await db_session.commit()

        reloaded = await repo.get_by_id(review.id)
        assert reloaded is not None
        assert reloaded.review_status is ReviewStatus.REJECTED


class TestGetByClinicalNoteId:
    async def test_returns_the_matching_review(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyDoctorReviewRepository(db_session)

        review = DoctorReview.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            clinical_note_id=note.id,
        )
        await repo.add(review)
        await db_session.commit()

        found = await repo.get_by_clinical_note_id(note.id)
        assert found is not None and found.id == review.id

    async def test_returns_none_for_a_clinical_note_without_a_review(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyDoctorReviewRepository(db_session)
        assert await repo.get_by_clinical_note_id(uuid4()) is None


class TestListByPatient:
    async def test_returns_reviews_scoped_to_the_patient(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        _org2, other_patient, other_doctor, other_visit, other_note = await persist_full_chain(
            db_session
        )
        repo = SqlAlchemyDoctorReviewRepository(db_session)

        await repo.add(
            DoctorReview.create(
                organization_id=organization.id,
                patient_id=patient.id,
                visit_id=visit.id,
                doctor_id=doctor.id,
                clinical_note_id=note.id,
            )
        )
        await repo.add(
            DoctorReview.create(
                organization_id=_org2.id,
                patient_id=other_patient.id,
                visit_id=other_visit.id,
                doctor_id=other_doctor.id,
                clinical_note_id=other_note.id,
            )
        )
        await db_session.commit()

        reviews = await repo.list_by_patient(patient.id)
        assert [r.patient_id for r in reviews] == [patient.id]

    async def test_returns_empty_list_for_a_patient_without_reviews(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyDoctorReviewRepository(db_session)
        assert await repo.list_by_patient(uuid4()) == []


class TestDuplicateReviewUniqueness:
    async def test_a_second_review_for_the_same_clinical_note_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyDoctorReviewRepository(db_session)

        first = DoctorReview.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            clinical_note_id=note.id,
        )
        await repo.add(first)
        await db_session.commit()

        second = DoctorReview.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            clinical_note_id=note.id,
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestDoctorReviewRequiresValidReferences:
    async def test_nonexistent_organization_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        _organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyDoctorReviewRepository(db_session)

        review = DoctorReview.create(
            organization_id=uuid4(),
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            clinical_note_id=note.id,
        )
        await repo.add(review)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_patient_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyDoctorReviewRepository(db_session)

        review = DoctorReview.create(
            organization_id=organization.id,
            patient_id=uuid4(),
            visit_id=visit.id,
            doctor_id=doctor.id,
            clinical_note_id=note.id,
        )
        await repo.add(review)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_visit_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, _visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyDoctorReviewRepository(db_session)

        review = DoctorReview.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=uuid4(),
            doctor_id=doctor.id,
            clinical_note_id=note.id,
        )
        await repo.add(review)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_doctor_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, _doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyDoctorReviewRepository(db_session)

        review = DoctorReview.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=uuid4(),
            clinical_note_id=note.id,
        )
        await repo.add(review)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_clinical_note_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, _note = await persist_full_chain(db_session)
        repo = SqlAlchemyDoctorReviewRepository(db_session)

        review = DoctorReview.create(
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            clinical_note_id=uuid4(),
        )
        await repo.add(review)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
