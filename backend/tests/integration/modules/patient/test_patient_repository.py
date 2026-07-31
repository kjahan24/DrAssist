"""Integration tests for `SqlAlchemyPatientRepository`, including the FK to
`organizations` and the per-organization `patient_number` uniqueness
constraint, against a real PostgreSQL instance."""

from datetime import UTC, date, datetime, timedelta
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


class TestPatientSearch:
    """Search & Filtering module — `SqlAlchemyPatientRepository.search`."""

    async def test_scopes_to_organization(self, db_session: AsyncSession) -> None:
        org_a = await persist_organization(db_session)
        org_b = await persist_organization(db_session)
        repo = SqlAlchemyPatientRepository(db_session)
        patient_a = Patient.register(
            organization_id=org_a.id,
            patient_number="PAT-A",
            first_name="Alpha",
            last_name="One",
            gender=Gender.FEMALE,
            date_of_birth=date(1990, 1, 1),
        )
        patient_b = Patient.register(
            organization_id=org_b.id,
            patient_number="PAT-B",
            first_name="Beta",
            last_name="Two",
            gender=Gender.MALE,
            date_of_birth=date(1990, 1, 1),
        )
        await repo.add(patient_a)
        await repo.add(patient_b)
        await db_session.commit()

        results, total = await repo.search(organization_id=org_a.id)

        assert total == 1
        assert [p.id for p in results] == [patient_a.id]

    async def test_query_matches_full_text_name_or_partial_patient_number(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyPatientRepository(db_session)
        by_name = Patient.register(
            organization_id=organization.id,
            patient_number="PAT-100",
            first_name="Warren",
            last_name="Smith",
            gender=Gender.MALE,
            date_of_birth=date(1990, 1, 1),
        )
        by_number = Patient.register(
            organization_id=organization.id,
            patient_number="PAT-SPECIAL-042",
            first_name="Alice",
            last_name="Jones",
            gender=Gender.FEMALE,
            date_of_birth=date(1990, 1, 1),
        )
        unrelated = Patient.register(
            organization_id=organization.id,
            patient_number="PAT-999",
            first_name="Nobody",
            last_name="Else",
            gender=Gender.FEMALE,
            date_of_birth=date(1990, 1, 1),
        )
        for patient in (by_name, by_number, unrelated):
            await repo.add(patient)
        await db_session.commit()

        name_results, name_total = await repo.search(
            organization_id=organization.id, query="warren"
        )
        number_results, number_total = await repo.search(
            organization_id=organization.id, query="SPECIAL-042"
        )

        assert name_total == 1
        assert [p.id for p in name_results] == [by_name.id]
        assert number_total == 1
        assert [p.id for p in number_results] == [by_number.id]

    async def test_status_filter_is_an_in_filter(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyPatientRepository(db_session)
        active = Patient.register(
            organization_id=organization.id,
            patient_number="PAT-ACTIVE",
            first_name="Active",
            last_name="Patient",
            gender=Gender.FEMALE,
            date_of_birth=date(1990, 1, 1),
        )
        inactive = Patient.register(
            organization_id=organization.id,
            patient_number="PAT-INACTIVE",
            first_name="Inactive",
            last_name="Patient",
            gender=Gender.FEMALE,
            date_of_birth=date(1990, 1, 1),
        )
        inactive.deactivate()
        await repo.add(active)
        await repo.add(inactive)
        await db_session.commit()

        results, total = await repo.search(
            organization_id=organization.id, statuses=[PatientStatus.INACTIVE]
        )

        assert total == 1
        assert [p.id for p in results] == [inactive.id]

    async def test_created_date_range_filter(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyPatientRepository(db_session)
        patient = Patient.register(
            organization_id=organization.id,
            patient_number="PAT-DATED",
            first_name="Dated",
            last_name="Patient",
            gender=Gender.FEMALE,
            date_of_birth=date(1990, 1, 1),
        )
        await repo.add(patient)
        await db_session.commit()

        past_window, _ = await repo.search(
            organization_id=organization.id,
            created_from=datetime.now(UTC) - timedelta(minutes=5),
        )
        future_window, future_total = await repo.search(
            organization_id=organization.id,
            created_from=datetime.now(UTC) + timedelta(days=1),
        )

        assert patient.id in [p.id for p in past_window]
        assert future_total == 0

    async def test_pagination_and_total_count(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyPatientRepository(db_session)
        for suffix in ("A", "B", "C"):
            await repo.add(
                Patient.register(
                    organization_id=organization.id,
                    patient_number=f"PAT-PAGE-{suffix}",
                    first_name=f"Page{suffix}",
                    last_name="Patient",
                    gender=Gender.FEMALE,
                    date_of_birth=date(1990, 1, 1),
                )
            )
        await db_session.commit()

        first_page, total = await repo.search(
            organization_id=organization.id,
            sort_by="patient_number",
            sort_order="asc",
            offset=0,
            limit=2,
        )
        second_page, _ = await repo.search(
            organization_id=organization.id,
            sort_by="patient_number",
            sort_order="asc",
            offset=2,
            limit=2,
        )

        assert total == 3
        assert [p.patient_number for p in first_page] == ["PAT-PAGE-A", "PAT-PAGE-B"]
        assert [p.patient_number for p in second_page] == ["PAT-PAGE-C"]

    async def test_sort_order_desc(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyPatientRepository(db_session)
        for suffix in ("A", "B"):
            await repo.add(
                Patient.register(
                    organization_id=organization.id,
                    patient_number=f"PAT-SORT-{suffix}",
                    first_name=f"Sort{suffix}",
                    last_name="Patient",
                    gender=Gender.FEMALE,
                    date_of_birth=date(1990, 1, 1),
                )
            )
        await db_session.commit()

        results, _ = await repo.search(
            organization_id=organization.id, sort_by="patient_number", sort_order="desc"
        )

        assert [p.patient_number for p in results] == ["PAT-SORT-B", "PAT-SORT-A"]
