"""Integration tests for `SqlAlchemyPatientMedicalConditionRepository`,
including the FKs to `patients`/`doctors` and the "one active condition
per patient + condition name (case-insensitive)" partial unique index,
against a real PostgreSQL instance."""

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.patient._helpers import persist_doctor, persist_patient

from app.modules.patient.domain.entities import PatientMedicalCondition
from app.modules.patient.domain.enums import ConditionSeverity, ConditionStatus
from app.modules.patient.domain.value_objects import ICD10Code
from app.modules.patient.infrastructure.models import PatientMedicalConditionModel
from app.modules.patient.infrastructure.repositories import (
    SqlAlchemyPatientMedicalConditionRepository,
)


class TestPatientMedicalConditionRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        patient = await persist_patient(db_session)
        doctor = await persist_doctor(db_session, organization_id=patient.organization_id)
        repo = SqlAlchemyPatientMedicalConditionRepository(db_session)

        condition = PatientMedicalCondition.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            condition_name="Type 2 Diabetes",
            category="Endocrine",
            severity=ConditionSeverity.MODERATE,
            diagnosis_date=date(2026, 1, 1),
            diagnosed_by=doctor.id,
            icd10_code=ICD10Code("E11.9"),
            onset_date=date(2025, 12, 1),
            is_chronic=True,
            is_infectious=False,
            notes="Managed with metformin",
        )
        await repo.add(condition)
        await db_session.commit()

        reloaded = await repo.get_by_id(condition.id)
        assert reloaded is not None
        assert reloaded.patient_id == patient.id
        assert reloaded.diagnosed_by == doctor.id
        assert reloaded.condition_name == "Type 2 Diabetes"
        assert reloaded.category == "Endocrine"
        assert reloaded.severity is ConditionSeverity.MODERATE
        assert str(reloaded.icd10_code) == "E11.9"
        assert reloaded.onset_date == date(2025, 12, 1)
        assert reloaded.is_chronic is True
        assert reloaded.is_infectious is False
        assert reloaded.notes == "Managed with metformin"
        assert reloaded.status is ConditionStatus.ACTIVE

    async def test_resolve_persists(self, db_session: AsyncSession) -> None:
        patient = await persist_patient(db_session)
        repo = SqlAlchemyPatientMedicalConditionRepository(db_session)

        condition = PatientMedicalCondition.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            condition_name="Bronchitis",
            category="Respiratory",
            severity=ConditionSeverity.MILD,
            diagnosis_date=date(2026, 1, 1),
        )
        await repo.add(condition)
        await db_session.commit()

        condition.resolve(resolved_date=date(2026, 1, 15))
        await repo.add(condition)
        await db_session.commit()

        reloaded = await repo.get_by_id(condition.id)
        assert reloaded is not None
        assert reloaded.status is ConditionStatus.RESOLVED
        assert reloaded.resolved_date == date(2026, 1, 15)

    async def test_list_by_patient_scopes_to_a_single_patient(
        self, db_session: AsyncSession
    ) -> None:
        patient_a = await persist_patient(db_session)
        patient_b = await persist_patient(db_session)
        repo = SqlAlchemyPatientMedicalConditionRepository(db_session)

        condition_a = PatientMedicalCondition.create(
            organization_id=patient_a.organization_id,
            patient_id=patient_a.id,
            condition_name="Type 2 Diabetes",
            category="Endocrine",
            severity=ConditionSeverity.MODERATE,
            diagnosis_date=date(2026, 1, 1),
        )
        condition_b = PatientMedicalCondition.create(
            organization_id=patient_b.organization_id,
            patient_id=patient_b.id,
            condition_name="Bronchitis",
            category="Respiratory",
            severity=ConditionSeverity.MILD,
            diagnosis_date=date(2026, 1, 1),
        )
        await repo.add(condition_a)
        await repo.add(condition_b)
        await db_session.commit()

        conditions_for_a = await repo.list_by_patient(patient_a.id)
        assert [c.id for c in conditions_for_a] == [condition_a.id]


class TestGetActiveByPatientAndConditionName:
    async def test_finds_the_active_condition_case_insensitively(
        self, db_session: AsyncSession
    ) -> None:
        patient = await persist_patient(db_session)
        repo = SqlAlchemyPatientMedicalConditionRepository(db_session)

        condition = PatientMedicalCondition.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            condition_name="Type 2 Diabetes",
            category="Endocrine",
            severity=ConditionSeverity.MODERATE,
            diagnosis_date=date(2026, 1, 1),
        )
        await repo.add(condition)
        await db_session.commit()

        found = await repo.get_active_by_patient_and_condition_name(
            patient_id=patient.id, condition_name="TYPE 2 DIABETES"
        )
        assert found is not None
        assert found.id == condition.id

    async def test_returns_none_for_a_resolved_condition(self, db_session: AsyncSession) -> None:
        patient = await persist_patient(db_session)
        repo = SqlAlchemyPatientMedicalConditionRepository(db_session)

        condition = PatientMedicalCondition.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            condition_name="Bronchitis",
            category="Respiratory",
            severity=ConditionSeverity.MILD,
            diagnosis_date=date(2026, 1, 1),
        )
        condition.resolve(resolved_date=date(2026, 1, 15))
        await repo.add(condition)
        await db_session.commit()

        found = await repo.get_active_by_patient_and_condition_name(
            patient_id=patient.id, condition_name="Bronchitis"
        )
        assert found is None


class TestDuplicateActiveConditionUniqueness:
    async def test_two_active_conditions_with_the_same_name_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        patient = await persist_patient(db_session)
        repo = SqlAlchemyPatientMedicalConditionRepository(db_session)

        first = PatientMedicalCondition.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            condition_name="Type 2 Diabetes",
            category="Endocrine",
            severity=ConditionSeverity.MODERATE,
            diagnosis_date=date(2026, 1, 1),
        )
        await repo.add(first)
        await db_session.commit()

        second = PatientMedicalCondition.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            condition_name="TYPE 2 DIABETES",
            category="Endocrine",
            severity=ConditionSeverity.SEVERE,
            diagnosis_date=date(2026, 2, 1),
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestPatientMedicalConditionRequiresValidReferences:
    async def test_nonexistent_patient_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization_id = (await persist_patient(db_session)).organization_id
        repo = SqlAlchemyPatientMedicalConditionRepository(db_session)

        condition = PatientMedicalCondition.create(
            organization_id=organization_id,
            patient_id=uuid4(),
            condition_name="Type 2 Diabetes",
            category="Endocrine",
            severity=ConditionSeverity.MODERATE,
            diagnosis_date=date(2026, 1, 1),
        )
        await repo.add(condition)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_diagnosing_doctor_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        patient = await persist_patient(db_session)
        repo = SqlAlchemyPatientMedicalConditionRepository(db_session)

        condition = PatientMedicalCondition.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            condition_name="Type 2 Diabetes",
            category="Endocrine",
            severity=ConditionSeverity.MODERATE,
            diagnosis_date=date(2026, 1, 1),
            diagnosed_by=uuid4(),
        )
        await repo.add(condition)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestResolvedDateCheckConstraint:
    async def test_a_resolved_date_not_after_diagnosis_date_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        """`PatientMedicalCondition.__post_init__` already prevents this
        state from ever existing via the domain layer — this test targets
        the DB `CHECK` constraint directly (bypassing the domain entity,
        the way a direct SQL edit would) to prove the defense-in-depth
        layer actually works."""
        patient = await persist_patient(db_session)

        model = PatientMedicalConditionModel(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            condition_name="Type 2 Diabetes",
            category="Endocrine",
            severity=ConditionSeverity.MODERATE,
            diagnosis_date=date(2026, 1, 10),
            status=ConditionStatus.RESOLVED,
            resolved_date=date(2026, 1, 1),
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestResolvedDateRequiredForChronicCheckConstraint:
    async def test_chronic_and_resolved_without_resolved_date_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        """Same defense-in-depth rationale as
        `TestResolvedDateCheckConstraint` above, for the "chronic
        conditions cannot have status 'Resolved' unless resolved_date
        exists" rule."""
        patient = await persist_patient(db_session)

        model = PatientMedicalConditionModel(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            condition_name="Type 2 Diabetes",
            category="Endocrine",
            severity=ConditionSeverity.MODERATE,
            diagnosis_date=date(2026, 1, 1),
            is_chronic=True,
            status=ConditionStatus.RESOLVED,
            resolved_date=None,
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
