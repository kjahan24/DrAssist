"""Integration tests for `SqlAlchemyClinicalReasoningRepository`,
including the FKs to `organizations`/`clinical_notes`/`patients`/
`patient_visits`/`doctors` and — unlike `soap_notes`/`prescriptions` —
the *absence* of any one-to-one uniqueness constraint on
`clinical_note_id` ("One Clinical Note may contain multiple Clinical
Reasoning records") and the *absence* of any globally-unique "number"
column at all, against a real PostgreSQL instance.

No `TestCheckConstraints` class here, matching
`tests.integration.modules.prescriptions.test_prescription_repository` —
like `prescriptions`, `clinical_reasoning` carries no `CHECK` constraints
at all (see `app/modules/clinical_reasoning/infrastructure/models.py` for
why "Approved/Rejected reasoning becomes immutable" has no database-level
enforcement layer)."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.clinical_reasoning._helpers import persist_full_chain

from app.modules.clinical_reasoning.domain.entities import ClinicalReasoning
from app.modules.clinical_reasoning.domain.enums import ReasoningSource, ReviewStatus
from app.modules.clinical_reasoning.infrastructure.repositories import (
    SqlAlchemyClinicalReasoningRepository,
)


class TestClinicalReasoningRoundTrip:
    async def test_save_and_reload_preserves_fields_for_ai_generated(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyClinicalReasoningRepository(db_session)

        reasoning = ClinicalReasoning.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            reasoning_source=ReasoningSource.AI,
            reasoning_text="Elevated WBC suggests possible infection.",
            ai_generated=True,
            confidence_score=0.87,
        )
        await repo.add(reasoning)
        await db_session.commit()

        reloaded = await repo.get_by_id(reasoning.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.clinical_note_id == note.id
        assert reloaded.patient_id == patient.id
        assert reloaded.visit_id == visit.id
        assert reloaded.doctor_id == doctor.id
        assert reloaded.reasoning_source is ReasoningSource.AI
        assert reloaded.reasoning_text == "Elevated WBC suggests possible infection."
        assert reloaded.ai_generated is True
        assert reloaded.review_status is ReviewStatus.PENDING
        assert reloaded.reviewed_by_doctor is False
        assert reloaded.confidence_score == 0.87

    async def test_save_and_reload_preserves_fields_for_physician_authored(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyClinicalReasoningRepository(db_session)

        reasoning = ClinicalReasoning.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            reasoning_source=ReasoningSource.PHYSICIAN,
            reasoning_text="Consistent with viral upper respiratory infection.",
            ai_generated=False,
        )
        await repo.add(reasoning)
        await db_session.commit()

        reloaded = await repo.get_by_id(reasoning.id)
        assert reloaded is not None
        assert reloaded.review_status is ReviewStatus.REVIEWED
        assert reloaded.reviewed_by_doctor is True
        assert reloaded.confidence_score is None

    async def test_full_review_workflow_persists(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyClinicalReasoningRepository(db_session)

        reasoning = ClinicalReasoning.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            reasoning_source=ReasoningSource.AI,
            reasoning_text="Elevated WBC suggests possible infection.",
            ai_generated=True,
        )
        await repo.add(reasoning)
        await db_session.commit()

        reasoning.mark_reviewed()
        await repo.add(reasoning)
        await db_session.commit()

        reasoning.approve()
        await repo.add(reasoning)
        await db_session.commit()

        reloaded = await repo.get_by_id(reasoning.id)
        assert reloaded is not None
        assert reloaded.review_status is ReviewStatus.APPROVED
        assert reloaded.reviewed_by_doctor is True

    async def test_rejection_persists(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyClinicalReasoningRepository(db_session)

        reasoning = ClinicalReasoning.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            reasoning_source=ReasoningSource.AI,
            reasoning_text="Elevated WBC suggests possible infection.",
            ai_generated=True,
        )
        await repo.add(reasoning)
        await db_session.commit()

        reasoning.reject()
        await repo.add(reasoning)
        await db_session.commit()

        reloaded = await repo.get_by_id(reasoning.id)
        assert reloaded is not None
        assert reloaded.review_status is ReviewStatus.REJECTED


class TestListByClinicalNote:
    async def test_multiple_records_for_the_same_clinical_note_are_all_returned(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyClinicalReasoningRepository(db_session)

        await repo.add(
            ClinicalReasoning.create(
                organization_id=organization.id,
                clinical_note_id=note.id,
                patient_id=patient.id,
                visit_id=visit.id,
                doctor_id=doctor.id,
                reasoning_source=ReasoningSource.AI,
                reasoning_text="First reasoning record",
                ai_generated=True,
            )
        )
        await repo.add(
            ClinicalReasoning.create(
                organization_id=organization.id,
                clinical_note_id=note.id,
                patient_id=patient.id,
                visit_id=visit.id,
                doctor_id=doctor.id,
                reasoning_source=ReasoningSource.PHYSICIAN,
                reasoning_text="Second reasoning record",
                ai_generated=False,
            )
        )
        await db_session.commit()

        records = await repo.list_by_clinical_note(note.id)
        assert {r.reasoning_text for r in records} == {
            "First reasoning record",
            "Second reasoning record",
        }

    async def test_returns_empty_list_for_a_clinical_note_without_records(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyClinicalReasoningRepository(db_session)
        assert await repo.list_by_clinical_note(uuid4()) == []


class TestListByPatient:
    async def test_returns_records_scoped_to_the_patient(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        _org2, other_patient, other_doctor, other_visit, other_note = await persist_full_chain(
            db_session
        )
        repo = SqlAlchemyClinicalReasoningRepository(db_session)

        await repo.add(
            ClinicalReasoning.create(
                organization_id=organization.id,
                clinical_note_id=note.id,
                patient_id=patient.id,
                visit_id=visit.id,
                doctor_id=doctor.id,
                reasoning_source=ReasoningSource.AI,
                reasoning_text="Reasoning for our patient",
                ai_generated=True,
            )
        )
        await repo.add(
            ClinicalReasoning.create(
                organization_id=_org2.id,
                clinical_note_id=other_note.id,
                patient_id=other_patient.id,
                visit_id=other_visit.id,
                doctor_id=other_doctor.id,
                reasoning_source=ReasoningSource.AI,
                reasoning_text="Reasoning for other patient",
                ai_generated=True,
            )
        )
        await db_session.commit()

        records = await repo.list_by_patient(patient.id)
        assert [r.reasoning_text for r in records] == ["Reasoning for our patient"]

    async def test_returns_empty_list_for_a_patient_without_records(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyClinicalReasoningRepository(db_session)
        assert await repo.list_by_patient(uuid4()) == []


class TestClinicalReasoningRequiresValidReferences:
    async def test_nonexistent_organization_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        _organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyClinicalReasoningRepository(db_session)

        reasoning = ClinicalReasoning.create(
            organization_id=uuid4(),
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            reasoning_source=ReasoningSource.AI,
            reasoning_text="Orphan org",
            ai_generated=True,
        )
        await repo.add(reasoning)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_clinical_note_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, _note = await persist_full_chain(db_session)
        repo = SqlAlchemyClinicalReasoningRepository(db_session)

        reasoning = ClinicalReasoning.create(
            organization_id=organization.id,
            clinical_note_id=uuid4(),
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            reasoning_source=ReasoningSource.AI,
            reasoning_text="Orphan note",
            ai_generated=True,
        )
        await repo.add(reasoning)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_patient_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyClinicalReasoningRepository(db_session)

        reasoning = ClinicalReasoning.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=uuid4(),
            visit_id=visit.id,
            doctor_id=doctor.id,
            reasoning_source=ReasoningSource.AI,
            reasoning_text="Orphan patient",
            ai_generated=True,
        )
        await repo.add(reasoning)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_visit_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, _visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyClinicalReasoningRepository(db_session)

        reasoning = ClinicalReasoning.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=uuid4(),
            doctor_id=doctor.id,
            reasoning_source=ReasoningSource.AI,
            reasoning_text="Orphan visit",
            ai_generated=True,
        )
        await repo.add(reasoning)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_doctor_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, _doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyClinicalReasoningRepository(db_session)

        reasoning = ClinicalReasoning.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=uuid4(),
            reasoning_source=ReasoningSource.AI,
            reasoning_text="Orphan doctor",
            ai_generated=True,
        )
        await repo.add(reasoning)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
