"""Integration tests for `SqlAlchemyPatientAllergyRepository`, including
the FKs to `patients`/`doctors` and the "one active allergy per patient +
allergen (case-insensitive)" partial unique index, against a real
PostgreSQL instance."""

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.patient._helpers import persist_doctor, persist_patient

from app.modules.patient.domain.entities import PatientAllergy
from app.modules.patient.domain.enums import AllergySeverity, AllergyStatus, AllergyType
from app.modules.patient.infrastructure.models import PatientAllergyModel
from app.modules.patient.infrastructure.repositories import SqlAlchemyPatientAllergyRepository


class TestPatientAllergyRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        patient = await persist_patient(db_session)
        doctor = await persist_doctor(db_session, organization_id=patient.organization_id)
        repo = SqlAlchemyPatientAllergyRepository(db_session)

        allergy = PatientAllergy.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            allergy_type=AllergyType.DRUG,
            allergen_name="Penicillin",
            severity=AllergySeverity.SEVERE,
            reaction="Anaphylaxis",
            onset_date=date(2020, 5, 1),
            notes="Confirmed via patient history",
            verified_by=doctor.id,
            verified_date=date(2026, 1, 1),
        )
        await repo.add(allergy)
        await db_session.commit()

        reloaded = await repo.get_by_id(allergy.id)
        assert reloaded is not None
        assert reloaded.patient_id == patient.id
        assert reloaded.allergy_type is AllergyType.DRUG
        assert reloaded.allergen_name == "Penicillin"
        assert reloaded.severity is AllergySeverity.SEVERE
        assert reloaded.reaction == "Anaphylaxis"
        assert reloaded.onset_date == date(2020, 5, 1)
        assert reloaded.verified_by == doctor.id
        assert reloaded.verified_date == date(2026, 1, 1)
        assert reloaded.status is AllergyStatus.ACTIVE

    async def test_status_change_persists(self, db_session: AsyncSession) -> None:
        patient = await persist_patient(db_session)
        repo = SqlAlchemyPatientAllergyRepository(db_session)

        allergy = PatientAllergy.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            allergy_type=AllergyType.FOOD,
            allergen_name="Peanuts",
            severity=AllergySeverity.MODERATE,
        )
        await repo.add(allergy)
        await db_session.commit()

        allergy.resolve()
        await repo.add(allergy)
        await db_session.commit()

        reloaded = await repo.get_by_id(allergy.id)
        assert reloaded is not None
        assert reloaded.status is AllergyStatus.RESOLVED

    async def test_list_by_patient_scopes_to_a_single_patient(
        self, db_session: AsyncSession
    ) -> None:
        patient_a = await persist_patient(db_session)
        patient_b = await persist_patient(db_session)
        repo = SqlAlchemyPatientAllergyRepository(db_session)

        allergy_a = PatientAllergy.create(
            organization_id=patient_a.organization_id,
            patient_id=patient_a.id,
            allergy_type=AllergyType.DRUG,
            allergen_name="Penicillin",
            severity=AllergySeverity.SEVERE,
        )
        allergy_b = PatientAllergy.create(
            organization_id=patient_b.organization_id,
            patient_id=patient_b.id,
            allergy_type=AllergyType.FOOD,
            allergen_name="Peanuts",
            severity=AllergySeverity.MILD,
        )
        await repo.add(allergy_a)
        await repo.add(allergy_b)
        await db_session.commit()

        allergies_for_a = await repo.list_by_patient(patient_a.id)
        assert [a.id for a in allergies_for_a] == [allergy_a.id]


class TestGetActiveByPatientAndAllergen:
    async def test_finds_the_active_allergy_case_insensitively(
        self, db_session: AsyncSession
    ) -> None:
        patient = await persist_patient(db_session)
        repo = SqlAlchemyPatientAllergyRepository(db_session)

        allergy = PatientAllergy.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            allergy_type=AllergyType.DRUG,
            allergen_name="Penicillin",
            severity=AllergySeverity.SEVERE,
        )
        await repo.add(allergy)
        await db_session.commit()

        found = await repo.get_active_by_patient_and_allergen(
            patient_id=patient.id, allergen_name="PENICILLIN"
        )
        assert found is not None
        assert found.id == allergy.id

    async def test_returns_none_for_a_resolved_allergy(self, db_session: AsyncSession) -> None:
        patient = await persist_patient(db_session)
        repo = SqlAlchemyPatientAllergyRepository(db_session)

        allergy = PatientAllergy.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            allergy_type=AllergyType.DRUG,
            allergen_name="Penicillin",
            severity=AllergySeverity.SEVERE,
        )
        allergy.resolve()
        await repo.add(allergy)
        await db_session.commit()

        found = await repo.get_active_by_patient_and_allergen(
            patient_id=patient.id, allergen_name="Penicillin"
        )
        assert found is None


class TestDuplicateActiveAllergyUniqueness:
    async def test_two_active_allergies_for_the_same_patient_and_allergen_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        patient = await persist_patient(db_session)
        repo = SqlAlchemyPatientAllergyRepository(db_session)

        first = PatientAllergy.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            allergy_type=AllergyType.DRUG,
            allergen_name="Penicillin",
            severity=AllergySeverity.SEVERE,
        )
        await repo.add(first)
        await db_session.commit()

        second = PatientAllergy.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            allergy_type=AllergyType.DRUG,
            allergen_name="PENICILLIN",
            severity=AllergySeverity.MILD,
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_a_resolved_and_a_new_active_allergy_for_the_same_allergen_coexist(
        self, db_session: AsyncSession
    ) -> None:
        patient = await persist_patient(db_session)
        repo = SqlAlchemyPatientAllergyRepository(db_session)

        first = PatientAllergy.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            allergy_type=AllergyType.DRUG,
            allergen_name="Penicillin",
            severity=AllergySeverity.SEVERE,
        )
        await repo.add(first)
        await db_session.commit()

        first.resolve()
        await repo.add(first)
        await db_session.commit()

        second = PatientAllergy.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            allergy_type=AllergyType.DRUG,
            allergen_name="Penicillin",
            severity=AllergySeverity.MILD,
        )
        await repo.add(second)
        await db_session.commit()

        reloaded_second = await repo.get_by_id(second.id)
        assert reloaded_second is not None
        assert reloaded_second.status is AllergyStatus.ACTIVE


class TestPatientAllergyRequiresValidReferences:
    async def test_nonexistent_patient_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization_id = (await persist_patient(db_session)).organization_id
        repo = SqlAlchemyPatientAllergyRepository(db_session)

        allergy = PatientAllergy.create(
            organization_id=organization_id,
            patient_id=uuid4(),
            allergy_type=AllergyType.DRUG,
            allergen_name="Penicillin",
            severity=AllergySeverity.SEVERE,
        )
        await repo.add(allergy)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_verifying_doctor_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        patient = await persist_patient(db_session)
        repo = SqlAlchemyPatientAllergyRepository(db_session)

        allergy = PatientAllergy.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            allergy_type=AllergyType.DRUG,
            allergen_name="Penicillin",
            severity=AllergySeverity.SEVERE,
            verified_by=uuid4(),
        )
        await repo.add(allergy)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestVerifiedDatePairingCheckConstraint:
    async def test_a_verified_date_without_verified_by_violates_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        """`PatientAllergy.__post_init__` already prevents this state from
        ever existing via the domain layer — this test targets the DB
        `CHECK` constraint directly (bypassing the domain entity, the way
        a direct SQL edit would) to prove the defense-in-depth layer
        actually works, not just the application-level guard."""
        patient = await persist_patient(db_session)

        model = PatientAllergyModel(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            allergy_type=AllergyType.DRUG,
            allergen_name="Penicillin",
            severity=AllergySeverity.SEVERE,
            verified_by=None,
            verified_date=date(2026, 1, 1),
        )
        db_session.add(model)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
