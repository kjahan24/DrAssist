"""Integration tests for `SqlAlchemyDifferentialDiagnosisRepository`,
including the FKs to `organizations`/`clinical_notes`/
`clinical_reasoning`/`patients`/`patient_visits`/`doctors`, the "ranking
must be unique within a Clinical Note" partial composite unique index,
and the `ranking >= 1` `CHECK` constraint, against a real PostgreSQL
instance.
"""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.differential_diagnosis._helpers import (
    persist_clinical_reasoning,
    persist_full_chain,
)

from app.modules.differential_diagnosis.domain.entities import DifferentialDiagnosis
from app.modules.differential_diagnosis.domain.enums import DiagnosisSource, ReviewStatus
from app.modules.differential_diagnosis.infrastructure.models import DifferentialDiagnosisModel
from app.modules.differential_diagnosis.infrastructure.repositories import (
    SqlAlchemyDifferentialDiagnosisRepository,
)


class TestDifferentialDiagnosisRoundTrip:
    async def test_save_and_reload_preserves_fields_for_ai_generated(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyDifferentialDiagnosisRepository(db_session)

        diagnosis = DifferentialDiagnosis.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            diagnosis_name="Community-acquired pneumonia",
            diagnosis_source=DiagnosisSource.AI,
            ranking=1,
            likelihood_score=0.72,
            supporting_evidence="Crackles, fever, productive cough",
        )
        await repo.add(diagnosis)
        await db_session.commit()

        reloaded = await repo.get_by_id(diagnosis.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.clinical_note_id == note.id
        assert reloaded.patient_id == patient.id
        assert reloaded.visit_id == visit.id
        assert reloaded.doctor_id == doctor.id
        assert reloaded.diagnosis_name == "Community-acquired pneumonia"
        assert reloaded.diagnosis_source is DiagnosisSource.AI
        assert reloaded.ranking == 1
        assert reloaded.review_status is ReviewStatus.PENDING
        assert reloaded.likelihood_score == 0.72
        assert reloaded.supporting_evidence == "Crackles, fever, productive cough"
        assert reloaded.excluded is False
        assert reloaded.clinical_reasoning_id is None

    async def test_save_and_reload_preserves_fields_for_physician_authored(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyDifferentialDiagnosisRepository(db_session)

        diagnosis = DifferentialDiagnosis.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            diagnosis_name="Bronchitis",
            diagnosis_source=DiagnosisSource.PHYSICIAN,
            ranking=1,
        )
        await repo.add(diagnosis)
        await db_session.commit()

        reloaded = await repo.get_by_id(diagnosis.id)
        assert reloaded is not None
        assert reloaded.review_status is ReviewStatus.REVIEWED

    async def test_save_with_clinical_reasoning_link_preserves_the_link(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        reasoning = await persist_clinical_reasoning(
            db_session,
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
        )
        repo = SqlAlchemyDifferentialDiagnosisRepository(db_session)

        diagnosis = DifferentialDiagnosis.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            diagnosis_name="Pneumonia",
            diagnosis_source=DiagnosisSource.AI,
            ranking=1,
            clinical_reasoning_id=reasoning.id,
        )
        await repo.add(diagnosis)
        await db_session.commit()

        reloaded = await repo.get_by_id(diagnosis.id)
        assert reloaded is not None
        assert reloaded.clinical_reasoning_id == reasoning.id

    async def test_full_review_workflow_persists(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyDifferentialDiagnosisRepository(db_session)

        diagnosis = DifferentialDiagnosis.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            diagnosis_name="Pneumonia",
            diagnosis_source=DiagnosisSource.AI,
            ranking=1,
        )
        await repo.add(diagnosis)
        await db_session.commit()

        diagnosis.mark_reviewed()
        await repo.add(diagnosis)
        await db_session.commit()

        diagnosis.approve()
        await repo.add(diagnosis)
        await db_session.commit()

        reloaded = await repo.get_by_id(diagnosis.id)
        assert reloaded is not None
        assert reloaded.review_status is ReviewStatus.APPROVED


class TestGetByClinicalNoteAndRanking:
    async def test_returns_the_matching_diagnosis(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyDifferentialDiagnosisRepository(db_session)

        diagnosis = DifferentialDiagnosis.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            diagnosis_name="Pneumonia",
            diagnosis_source=DiagnosisSource.AI,
            ranking=1,
        )
        await repo.add(diagnosis)
        await db_session.commit()

        found = await repo.get_by_clinical_note_and_ranking(clinical_note_id=note.id, ranking=1)
        assert found is not None and found.id == diagnosis.id

    async def test_returns_none_for_an_unmatched_ranking(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyDifferentialDiagnosisRepository(db_session)
        assert (
            await repo.get_by_clinical_note_and_ranking(clinical_note_id=uuid4(), ranking=1) is None
        )


class TestListByClinicalNote:
    async def test_returns_diagnoses_ordered_by_ranking(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyDifferentialDiagnosisRepository(db_session)

        await repo.add(
            DifferentialDiagnosis.create(
                organization_id=organization.id,
                clinical_note_id=note.id,
                patient_id=patient.id,
                visit_id=visit.id,
                doctor_id=doctor.id,
                diagnosis_name="Bronchitis",
                diagnosis_source=DiagnosisSource.AI,
                ranking=2,
            )
        )
        await repo.add(
            DifferentialDiagnosis.create(
                organization_id=organization.id,
                clinical_note_id=note.id,
                patient_id=patient.id,
                visit_id=visit.id,
                doctor_id=doctor.id,
                diagnosis_name="Pneumonia",
                diagnosis_source=DiagnosisSource.AI,
                ranking=1,
            )
        )
        await db_session.commit()

        diagnoses = await repo.list_by_clinical_note(note.id)
        assert [d.diagnosis_name for d in diagnoses] == ["Pneumonia", "Bronchitis"]

    async def test_returns_empty_list_for_a_clinical_note_without_diagnoses(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyDifferentialDiagnosisRepository(db_session)
        assert await repo.list_by_clinical_note(uuid4()) == []


class TestListByPatient:
    async def test_returns_diagnoses_scoped_to_the_patient(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        _org2, other_patient, other_doctor, other_visit, other_note = await persist_full_chain(
            db_session
        )
        repo = SqlAlchemyDifferentialDiagnosisRepository(db_session)

        await repo.add(
            DifferentialDiagnosis.create(
                organization_id=organization.id,
                clinical_note_id=note.id,
                patient_id=patient.id,
                visit_id=visit.id,
                doctor_id=doctor.id,
                diagnosis_name="For our patient",
                diagnosis_source=DiagnosisSource.AI,
                ranking=1,
            )
        )
        await repo.add(
            DifferentialDiagnosis.create(
                organization_id=_org2.id,
                clinical_note_id=other_note.id,
                patient_id=other_patient.id,
                visit_id=other_visit.id,
                doctor_id=other_doctor.id,
                diagnosis_name="For other patient",
                diagnosis_source=DiagnosisSource.AI,
                ranking=1,
            )
        )
        await db_session.commit()

        diagnoses = await repo.list_by_patient(patient.id)
        assert [d.diagnosis_name for d in diagnoses] == ["For our patient"]

    async def test_returns_empty_list_for_a_patient_without_diagnoses(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyDifferentialDiagnosisRepository(db_session)
        assert await repo.list_by_patient(uuid4()) == []


class TestRankingUniqueness:
    async def test_duplicate_ranking_within_the_same_clinical_note_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyDifferentialDiagnosisRepository(db_session)

        first = DifferentialDiagnosis.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            diagnosis_name="Pneumonia",
            diagnosis_source=DiagnosisSource.AI,
            ranking=1,
        )
        await repo.add(first)
        await db_session.commit()

        second = DifferentialDiagnosis.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            diagnosis_name="Bronchitis",
            diagnosis_source=DiagnosisSource.AI,
            ranking=1,
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestDifferentialDiagnosisRequiresValidReferences:
    async def test_nonexistent_organization_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        _organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyDifferentialDiagnosisRepository(db_session)

        diagnosis = DifferentialDiagnosis.create(
            organization_id=uuid4(),
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            diagnosis_name="Orphan org",
            diagnosis_source=DiagnosisSource.AI,
            ranking=1,
        )
        await repo.add(diagnosis)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_clinical_note_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, _note = await persist_full_chain(db_session)
        repo = SqlAlchemyDifferentialDiagnosisRepository(db_session)

        diagnosis = DifferentialDiagnosis.create(
            organization_id=organization.id,
            clinical_note_id=uuid4(),
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            diagnosis_name="Orphan note",
            diagnosis_source=DiagnosisSource.AI,
            ranking=1,
        )
        await repo.add(diagnosis)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_clinical_reasoning_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyDifferentialDiagnosisRepository(db_session)

        diagnosis = DifferentialDiagnosis.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            diagnosis_name="Orphan reasoning link",
            diagnosis_source=DiagnosisSource.AI,
            ranking=1,
            clinical_reasoning_id=uuid4(),
        )
        await repo.add(diagnosis)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_patient_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyDifferentialDiagnosisRepository(db_session)

        diagnosis = DifferentialDiagnosis.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=uuid4(),
            visit_id=visit.id,
            doctor_id=doctor.id,
            diagnosis_name="Orphan patient",
            diagnosis_source=DiagnosisSource.AI,
            ranking=1,
        )
        await repo.add(diagnosis)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_visit_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, _visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyDifferentialDiagnosisRepository(db_session)

        diagnosis = DifferentialDiagnosis.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=uuid4(),
            doctor_id=doctor.id,
            diagnosis_name="Orphan visit",
            diagnosis_source=DiagnosisSource.AI,
            ranking=1,
        )
        await repo.add(diagnosis)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_doctor_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, _doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyDifferentialDiagnosisRepository(db_session)

        diagnosis = DifferentialDiagnosis.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=uuid4(),
            diagnosis_name="Orphan doctor",
            diagnosis_source=DiagnosisSource.AI,
            ranking=1,
        )
        await repo.add(diagnosis)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestCheckConstraints:
    """`DifferentialDiagnosis.__post_init__` already prevents `ranking < 1`
    from ever existing via the domain layer — this test targets the DB
    `CHECK` constraint directly (bypassing the domain entity, the way a
    direct SQL edit would) to prove the defense-in-depth layer actually
    works, the same pattern
    `tests.integration.modules.clinical_notes.test_clinical_note_repository.TestCheckConstraints`
    already established."""

    async def test_ranking_below_one_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)

        model = DifferentialDiagnosisModel(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            diagnosis_name="Bad ranking",
            diagnosis_source=DiagnosisSource.AI,
            ranking=0,
            review_status=ReviewStatus.PENDING,
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
