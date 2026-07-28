"""Integration tests for `SqlAlchemyPatientContactRepository`, including
the FK to `patients` and the "one primary contact per contact type"
partial unique index, against a real PostgreSQL instance."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.patient._helpers import persist_patient

from app.modules.patient.domain.entities import PatientContact
from app.modules.patient.domain.enums import ContactType
from app.modules.patient.infrastructure.repositories import SqlAlchemyPatientContactRepository
from app.shared.domain.common_value_objects import EmailAddress, PhoneNumber


class TestPatientContactRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        patient = await persist_patient(db_session)
        repo = SqlAlchemyPatientContactRepository(db_session)

        contact = PatientContact.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            contact_type=ContactType.MOBILE,
            phone_number=PhoneNumber("+1 555 0100"),
            email=EmailAddress("contact@example.com"),
            is_verified=True,
        )
        await repo.add(contact)
        await db_session.commit()

        reloaded = await repo.get_by_id(contact.id)
        assert reloaded is not None
        assert reloaded.patient_id == patient.id
        assert reloaded.contact_type is ContactType.MOBILE
        assert str(reloaded.phone_number) == "+1 555 0100"
        assert str(reloaded.email) == "contact@example.com"
        assert reloaded.is_verified is True

    async def test_list_by_patient_scopes_to_a_single_patient(
        self, db_session: AsyncSession
    ) -> None:
        patient_a = await persist_patient(db_session)
        patient_b = await persist_patient(db_session)
        repo = SqlAlchemyPatientContactRepository(db_session)

        contact_a = PatientContact.create(
            organization_id=patient_a.organization_id,
            patient_id=patient_a.id,
            contact_type=ContactType.MOBILE,
            phone_number=PhoneNumber("+1 555 0100"),
        )
        contact_b = PatientContact.create(
            organization_id=patient_b.organization_id,
            patient_id=patient_b.id,
            contact_type=ContactType.HOME,
            phone_number=PhoneNumber("+1 555 0200"),
        )
        await repo.add(contact_a)
        await repo.add(contact_b)
        await db_session.commit()

        contacts_for_a = await repo.list_by_patient(patient_a.id)
        assert [c.id for c in contacts_for_a] == [contact_a.id]


class TestUnsetPrimaryForPatientAndType:
    async def test_clears_is_primary_only_for_the_matching_contact_type(
        self, db_session: AsyncSession
    ) -> None:
        patient = await persist_patient(db_session)
        repo = SqlAlchemyPatientContactRepository(db_session)

        mobile = PatientContact.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            contact_type=ContactType.MOBILE,
            phone_number=PhoneNumber("+1 555 0100"),
            is_primary=True,
        )
        home = PatientContact.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            contact_type=ContactType.HOME,
            phone_number=PhoneNumber("+1 555 0200"),
            is_primary=True,
        )
        await repo.add(mobile)
        await repo.add(home)
        await db_session.commit()

        await repo.unset_primary_for_patient_and_type(patient.id, ContactType.MOBILE)
        await db_session.commit()

        reloaded_mobile = await repo.get_by_id(mobile.id)
        reloaded_home = await repo.get_by_id(home.id)
        assert reloaded_mobile is not None and reloaded_mobile.is_primary is False
        assert reloaded_home is not None and reloaded_home.is_primary is True


class TestPatientContactPrimaryUniqueness:
    async def test_two_primary_contacts_of_the_same_type_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        patient = await persist_patient(db_session)
        repo = SqlAlchemyPatientContactRepository(db_session)

        first = PatientContact.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            contact_type=ContactType.MOBILE,
            phone_number=PhoneNumber("+1 555 0100"),
            is_primary=True,
        )
        await repo.add(first)
        await db_session.commit()

        second = PatientContact.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            contact_type=ContactType.MOBILE,
            phone_number=PhoneNumber("+1 555 0200"),
            is_primary=True,
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestPatientContactRequiresValidPatient:
    async def test_nonexistent_patient_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization = (await persist_patient(db_session)).organization_id
        repo = SqlAlchemyPatientContactRepository(db_session)

        contact = PatientContact.create(
            organization_id=organization,
            patient_id=uuid4(),
            contact_type=ContactType.MOBILE,
            phone_number=PhoneNumber("+1 555 0100"),
        )
        await repo.add(contact)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
