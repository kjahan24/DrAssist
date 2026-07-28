"""Integration tests for `SqlAlchemyPatientRepository`, including the FK to
`organizations` and the per-organization `patient_number` uniqueness
constraint, against a real PostgreSQL instance."""

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.patient._helpers import persist_organization

from app.modules.patient.domain.entities import Patient
from app.modules.patient.domain.enums import BloodGroup, Gender, MaritalStatus, PatientStatus
from app.modules.patient.infrastructure.repositories import SqlAlchemyPatientRepository
from app.shared.domain.common_value_objects import EmailAddress, PhoneNumber


class TestPatientRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyPatientRepository(db_session)

        patient = Patient.register(
            organization_id=organization.id,
            patient_number="PAT-001",
            first_name="Jane",
            last_name="Doe",
            gender=Gender.FEMALE,
            date_of_birth=date(1990, 1, 1),
            blood_group=BloodGroup.O_POSITIVE,
            marital_status=MaritalStatus.MARRIED,
            phone=PhoneNumber("+1 555 0100"),
            email=EmailAddress("jane.doe@example.com"),
            city="Springfield",
        )
        await repo.add(patient)
        await db_session.commit()

        reloaded = await repo.get_by_id(patient.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.patient_number == "PAT-001"
        assert reloaded.first_name == "Jane"
        assert reloaded.gender is Gender.FEMALE
        assert reloaded.blood_group is BloodGroup.O_POSITIVE
        assert reloaded.marital_status is MaritalStatus.MARRIED
        assert str(reloaded.phone) == "+1 555 0100"
        assert str(reloaded.email) == "jane.doe@example.com"
        assert reloaded.city == "Springfield"
        assert reloaded.status is PatientStatus.ACTIVE

    async def test_update_details_persists(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyPatientRepository(db_session)

        patient = Patient.register(
            organization_id=organization.id,
            patient_number="PAT-002",
            first_name="Jane",
            last_name="Doe",
            gender=Gender.FEMALE,
            date_of_birth=date(1990, 1, 1),
        )
        await repo.add(patient)
        await db_session.commit()

        patient.update_details(city="Metropolis", remarks="Prefers morning appointments")
        await repo.add(patient)
        await db_session.commit()

        reloaded = await repo.get_by_id(patient.id)
        assert reloaded is not None
        assert reloaded.city == "Metropolis"
        assert reloaded.remarks == "Prefers morning appointments"

    async def test_status_change_persists(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyPatientRepository(db_session)

        patient = Patient.register(
            organization_id=organization.id,
            patient_number="PAT-003",
            first_name="Jane",
            last_name="Doe",
            gender=Gender.FEMALE,
            date_of_birth=date(1990, 1, 1),
        )
        await repo.add(patient)
        await db_session.commit()

        patient.mark_deceased()
        await repo.add(patient)
        await db_session.commit()

        reloaded = await repo.get_by_id(patient.id)
        assert reloaded is not None
        assert reloaded.status is PatientStatus.DECEASED


class TestPatientLookups:
    async def test_get_by_patient_number_scopes_to_organization(
        self, db_session: AsyncSession
    ) -> None:
        org_a = await persist_organization(db_session)
        org_b = await persist_organization(db_session)
        repo = SqlAlchemyPatientRepository(db_session)

        patient_a = Patient.register(
            organization_id=org_a.id,
            patient_number="SHARED-CODE",
            first_name="Jane",
            last_name="Doe",
            gender=Gender.FEMALE,
            date_of_birth=date(1990, 1, 1),
        )
        patient_b = Patient.register(
            organization_id=org_b.id,
            patient_number="SHARED-CODE",
            first_name="John",
            last_name="Smith",
            gender=Gender.MALE,
            date_of_birth=date(1985, 6, 15),
        )
        await repo.add(patient_a)
        await repo.add(patient_b)
        await db_session.commit()

        found_in_a = await repo.get_by_patient_number(
            organization_id=org_a.id, patient_number="SHARED-CODE"
        )
        found_in_b = await repo.get_by_patient_number(
            organization_id=org_b.id, patient_number="SHARED-CODE"
        )
        assert found_in_a is not None and found_in_a.id == patient_a.id
        assert found_in_b is not None and found_in_b.id == patient_b.id

    async def test_list_by_organization_scopes_to_a_single_organization(
        self, db_session: AsyncSession
    ) -> None:
        org_a = await persist_organization(db_session)
        org_b = await persist_organization(db_session)
        repo = SqlAlchemyPatientRepository(db_session)

        patient_a = Patient.register(
            organization_id=org_a.id,
            patient_number="PAT-A",
            first_name="Jane",
            last_name="Doe",
            gender=Gender.FEMALE,
            date_of_birth=date(1990, 1, 1),
        )
        patient_b = Patient.register(
            organization_id=org_b.id,
            patient_number="PAT-B",
            first_name="John",
            last_name="Smith",
            gender=Gender.MALE,
            date_of_birth=date(1985, 6, 15),
        )
        await repo.add(patient_a)
        await repo.add(patient_b)
        await db_session.commit()

        patients_for_a = await repo.list_by_organization(org_a.id)
        assert [p.id for p in patients_for_a] == [patient_a.id]


class TestPatientNumberUniqueness:
    async def test_duplicate_patient_number_within_organization_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyPatientRepository(db_session)

        first = Patient.register(
            organization_id=organization.id,
            patient_number="DUPLICATE",
            first_name="Jane",
            last_name="Doe",
            gender=Gender.FEMALE,
            date_of_birth=date(1990, 1, 1),
        )
        await repo.add(first)
        await db_session.commit()

        second = Patient.register(
            organization_id=organization.id,
            patient_number="DUPLICATE",
            first_name="John",
            last_name="Smith",
            gender=Gender.MALE,
            date_of_birth=date(1985, 6, 15),
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestPatientRequiresValidOrganization:
    async def test_nonexistent_organization_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyPatientRepository(db_session)
        patient = Patient.register(
            organization_id=uuid4(),
            patient_number="ORPHAN",
            first_name="Jane",
            last_name="Doe",
            gender=Gender.FEMALE,
            date_of_birth=date(1990, 1, 1),
        )
        await repo.add(patient)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestPatientNumericFieldsRoundTrip:
    async def test_optional_consultation_style_fields_round_trip(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyPatientRepository(db_session)

        patient = Patient.register(
            organization_id=organization.id,
            patient_number="PAT-004",
            first_name="Jane",
            last_name="Doe",
            gender=Gender.FEMALE,
            date_of_birth=date(1990, 1, 1),
            national_id="N123456",
            passport_number="P987654",
            occupation="Engineer",
            nationality="Wakandan",
            language="en",
            religion=None,
        )
        await repo.add(patient)
        await db_session.commit()

        reloaded = await repo.get_by_id(patient.id)
        assert reloaded is not None
        assert reloaded.national_id == "N123456"
        assert reloaded.passport_number == "P987654"
        assert reloaded.occupation == "Engineer"
        assert reloaded.nationality == "Wakandan"
        assert reloaded.religion is None
        assert reloaded.date_of_birth == date(1990, 1, 1)
