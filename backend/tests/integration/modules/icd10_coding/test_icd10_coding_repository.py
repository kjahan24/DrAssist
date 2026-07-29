"""Integration tests for `SqlAlchemyICD10CodingRepository`, including the
FKs to `organizations`/`clinical_notes`/`differential_diagnoses`/
`patients`/`patient_visits`/`doctors`, the "duplicate ICD-10 prevention
within a Clinical Note" partial composite unique index, and the "only
one Primary per Clinical Note" partial unique index, against a real
PostgreSQL instance.
"""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.icd10_coding._helpers import (
    persist_differential_diagnosis,
    persist_full_chain,
)

from app.modules.icd10_coding.domain.entities import ICD10Coding
from app.modules.icd10_coding.domain.enums import CodingSource, ReviewStatus
from app.modules.icd10_coding.infrastructure.repositories import (
    SqlAlchemyICD10CodingRepository,
)


class TestICD10CodingRoundTrip:
    async def test_save_and_reload_preserves_fields_for_ai_generated(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyICD10CodingRepository(db_session)

        coding = ICD10Coding.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            icd10_code="j18.9",
            diagnosis_title="Pneumonia, unspecified organism",
            coding_source=CodingSource.AI,
            coding_notes="Confirmed via chest X-ray",
        )
        await repo.add(coding)
        await db_session.commit()

        reloaded = await repo.get_by_id(coding.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.clinical_note_id == note.id
        assert reloaded.patient_id == patient.id
        assert reloaded.visit_id == visit.id
        assert reloaded.doctor_id == doctor.id
        assert reloaded.icd10_code == "J18.9"
        assert reloaded.diagnosis_title == "Pneumonia, unspecified organism"
        assert reloaded.coding_source is CodingSource.AI
        assert reloaded.review_status is ReviewStatus.PENDING
        assert reloaded.primary_code is False
        assert reloaded.coding_notes == "Confirmed via chest X-ray"
        assert reloaded.differential_diagnosis_id is None

    async def test_save_and_reload_preserves_fields_for_physician_generated(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyICD10CodingRepository(db_session)

        coding = ICD10Coding.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            icd10_code="R05",
            diagnosis_title="Cough",
            coding_source=CodingSource.PHYSICIAN,
        )
        await repo.add(coding)
        await db_session.commit()

        reloaded = await repo.get_by_id(coding.id)
        assert reloaded is not None
        assert reloaded.review_status is ReviewStatus.REVIEWED

    async def test_save_with_differential_diagnosis_link_preserves_the_link(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        diagnosis = await persist_differential_diagnosis(
            db_session,
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
        )
        repo = SqlAlchemyICD10CodingRepository(db_session)

        coding = ICD10Coding.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            icd10_code="J18.9",
            diagnosis_title="Pneumonia",
            coding_source=CodingSource.AI,
            differential_diagnosis_id=diagnosis.id,
        )
        await repo.add(coding)
        await db_session.commit()

        reloaded = await repo.get_by_id(coding.id)
        assert reloaded is not None
        assert reloaded.differential_diagnosis_id == diagnosis.id

    async def test_full_review_workflow_persists(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyICD10CodingRepository(db_session)

        coding = ICD10Coding.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            icd10_code="J18.9",
            diagnosis_title="Pneumonia",
            coding_source=CodingSource.AI,
        )
        await repo.add(coding)
        await db_session.commit()

        coding.mark_reviewed()
        await repo.add(coding)
        await db_session.commit()

        coding.approve()
        await repo.add(coding)
        await db_session.commit()

        reloaded = await repo.get_by_id(coding.id)
        assert reloaded is not None
        assert reloaded.review_status is ReviewStatus.APPROVED

    async def test_primary_code_workflow_persists(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyICD10CodingRepository(db_session)

        coding = ICD10Coding.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            icd10_code="J18.9",
            diagnosis_title="Pneumonia",
            coding_source=CodingSource.AI,
        )
        await repo.add(coding)
        await db_session.commit()

        coding.mark_as_primary()
        await repo.add(coding)
        await db_session.commit()

        reloaded = await repo.get_by_id(coding.id)
        assert reloaded is not None
        assert reloaded.primary_code is True

        reloaded.unmark_as_primary()
        await repo.add(reloaded)
        await db_session.commit()

        reloaded_again = await repo.get_by_id(coding.id)
        assert reloaded_again is not None
        assert reloaded_again.primary_code is False


class TestGetPrimaryForClinicalNote:
    async def test_returns_the_primary_coding(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyICD10CodingRepository(db_session)

        await repo.add(
            ICD10Coding.create(
                organization_id=organization.id,
                clinical_note_id=note.id,
                patient_id=patient.id,
                visit_id=visit.id,
                doctor_id=doctor.id,
                icd10_code="R05",
                diagnosis_title="Cough",
                coding_source=CodingSource.AI,
            )
        )
        primary = ICD10Coding.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            icd10_code="J18.9",
            diagnosis_title="Pneumonia",
            coding_source=CodingSource.AI,
            primary_code=True,
        )
        await repo.add(primary)
        await db_session.commit()

        found = await repo.get_primary_for_clinical_note(note.id)
        assert found is not None and found.id == primary.id

    async def test_returns_none_when_no_code_is_primary(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyICD10CodingRepository(db_session)
        assert await repo.get_primary_for_clinical_note(uuid4()) is None


class TestListByClinicalNote:
    async def test_returns_codes_ordered_by_creation(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyICD10CodingRepository(db_session)

        first = ICD10Coding.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            icd10_code="J18.9",
            diagnosis_title="Pneumonia",
            coding_source=CodingSource.AI,
        )
        await repo.add(first)
        await db_session.commit()

        second = ICD10Coding.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            icd10_code="R05",
            diagnosis_title="Cough",
            coding_source=CodingSource.AI,
        )
        await repo.add(second)
        await db_session.commit()

        codings = await repo.list_by_clinical_note(note.id)
        assert [c.icd10_code for c in codings] == ["J18.9", "R05"]

    async def test_returns_empty_list_for_a_clinical_note_without_codes(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyICD10CodingRepository(db_session)
        assert await repo.list_by_clinical_note(uuid4()) == []


class TestListByPatient:
    async def test_returns_codes_scoped_to_the_patient(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        _org2, other_patient, other_doctor, other_visit, other_note = await persist_full_chain(
            db_session
        )
        repo = SqlAlchemyICD10CodingRepository(db_session)

        await repo.add(
            ICD10Coding.create(
                organization_id=organization.id,
                clinical_note_id=note.id,
                patient_id=patient.id,
                visit_id=visit.id,
                doctor_id=doctor.id,
                icd10_code="J18.9",
                diagnosis_title="For our patient",
                coding_source=CodingSource.AI,
            )
        )
        await repo.add(
            ICD10Coding.create(
                organization_id=_org2.id,
                clinical_note_id=other_note.id,
                patient_id=other_patient.id,
                visit_id=other_visit.id,
                doctor_id=other_doctor.id,
                icd10_code="R05",
                diagnosis_title="For other patient",
                coding_source=CodingSource.AI,
            )
        )
        await db_session.commit()

        codings = await repo.list_by_patient(patient.id)
        assert [c.diagnosis_title for c in codings] == ["For our patient"]

    async def test_returns_empty_list_for_a_patient_without_codes(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyICD10CodingRepository(db_session)
        assert await repo.list_by_patient(uuid4()) == []


class TestICD10CodeUniqueness:
    async def test_duplicate_icd10_code_within_the_same_clinical_note_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyICD10CodingRepository(db_session)

        first = ICD10Coding.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            icd10_code="J18.9",
            diagnosis_title="Pneumonia",
            coding_source=CodingSource.AI,
        )
        await repo.add(first)
        await db_session.commit()

        second = ICD10Coding.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            icd10_code="j18.9",
            diagnosis_title="Pneumonia, duplicate",
            coding_source=CodingSource.AI,
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestPrimaryCodeUniqueness:
    async def test_two_primary_codes_within_the_same_clinical_note_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyICD10CodingRepository(db_session)

        first = ICD10Coding.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            icd10_code="J18.9",
            diagnosis_title="Pneumonia",
            coding_source=CodingSource.AI,
            primary_code=True,
        )
        await repo.add(first)
        await db_session.commit()

        second = ICD10Coding.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            icd10_code="R05",
            diagnosis_title="Cough",
            coding_source=CodingSource.AI,
            primary_code=True,
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestICD10CodingRequiresValidReferences:
    async def test_nonexistent_organization_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        _organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyICD10CodingRepository(db_session)

        coding = ICD10Coding.create(
            organization_id=uuid4(),
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            icd10_code="J18.9",
            diagnosis_title="Orphan org",
            coding_source=CodingSource.AI,
        )
        await repo.add(coding)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_clinical_note_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, _note = await persist_full_chain(db_session)
        repo = SqlAlchemyICD10CodingRepository(db_session)

        coding = ICD10Coding.create(
            organization_id=organization.id,
            clinical_note_id=uuid4(),
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            icd10_code="J18.9",
            diagnosis_title="Orphan note",
            coding_source=CodingSource.AI,
        )
        await repo.add(coding)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_differential_diagnosis_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyICD10CodingRepository(db_session)

        coding = ICD10Coding.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            icd10_code="J18.9",
            diagnosis_title="Orphan diagnosis link",
            coding_source=CodingSource.AI,
            differential_diagnosis_id=uuid4(),
        )
        await repo.add(coding)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_patient_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyICD10CodingRepository(db_session)

        coding = ICD10Coding.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=uuid4(),
            visit_id=visit.id,
            doctor_id=doctor.id,
            icd10_code="J18.9",
            diagnosis_title="Orphan patient",
            coding_source=CodingSource.AI,
        )
        await repo.add(coding)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_visit_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, _visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyICD10CodingRepository(db_session)

        coding = ICD10Coding.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=uuid4(),
            doctor_id=doctor.id,
            icd10_code="J18.9",
            diagnosis_title="Orphan visit",
            coding_source=CodingSource.AI,
        )
        await repo.add(coding)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_doctor_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, _doctor, visit, note = await persist_full_chain(db_session)
        repo = SqlAlchemyICD10CodingRepository(db_session)

        coding = ICD10Coding.create(
            organization_id=organization.id,
            clinical_note_id=note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=uuid4(),
            icd10_code="J18.9",
            diagnosis_title="Orphan doctor",
            coding_source=CodingSource.AI,
        )
        await repo.add(coding)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
