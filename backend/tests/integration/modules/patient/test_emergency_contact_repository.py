"""Integration tests for `SqlAlchemyEmergencyContactRepository`, including
the FK to `patients` and the "one primary emergency contact" partial
unique index, against a real PostgreSQL instance."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.patient._helpers import persist_patient

from app.modules.patient.domain.entities import EmergencyContact
from app.modules.patient.infrastructure.repositories import SqlAlchemyEmergencyContactRepository
from app.shared.domain.common_value_objects import PhoneNumber


class TestEmergencyContactRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        patient = await persist_patient(db_session)
        repo = SqlAlchemyEmergencyContactRepository(db_session)

        contact = EmergencyContact.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            full_name="John Doe",
            relationship="Spouse",
            phone_number=PhoneNumber("+1 555 0100"),
            address="123 Main St",
            priority=1,
        )
        await repo.add(contact)
        await db_session.commit()

        reloaded = await repo.get_by_id(contact.id)
        assert reloaded is not None
        assert reloaded.patient_id == patient.id
        assert reloaded.full_name == "John Doe"
        assert reloaded.relationship == "Spouse"
        assert str(reloaded.phone_number) == "+1 555 0100"
        assert reloaded.address == "123 Main St"
        assert reloaded.priority == 1

    async def test_list_by_patient_scopes_to_a_single_patient(
        self, db_session: AsyncSession
    ) -> None:
        patient_a = await persist_patient(db_session)
        patient_b = await persist_patient(db_session)
        repo = SqlAlchemyEmergencyContactRepository(db_session)

        contact_a = EmergencyContact.create(
            organization_id=patient_a.organization_id,
            patient_id=patient_a.id,
            full_name="John Doe",
            relationship="Spouse",
            phone_number=PhoneNumber("+1 555 0100"),
        )
        contact_b = EmergencyContact.create(
            organization_id=patient_b.organization_id,
            patient_id=patient_b.id,
            full_name="Jane Smith",
            relationship="Sister",
            phone_number=PhoneNumber("+1 555 0200"),
        )
        await repo.add(contact_a)
        await repo.add(contact_b)
        await db_session.commit()

        contacts_for_a = await repo.list_by_patient(patient_a.id)
        assert [c.id for c in contacts_for_a] == [contact_a.id]


class TestUnsetPrimaryForPatient:
    async def test_clears_is_primary_on_all_of_a_patients_emergency_contacts(
        self, db_session: AsyncSession
    ) -> None:
        patient = await persist_patient(db_session)
        repo = SqlAlchemyEmergencyContactRepository(db_session)

        contact = EmergencyContact.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            full_name="John Doe",
            relationship="Spouse",
            phone_number=PhoneNumber("+1 555 0100"),
            is_primary=True,
        )
        await repo.add(contact)
        await db_session.commit()

        await repo.unset_primary_for_patient(patient.id)
        await db_session.commit()

        reloaded = await repo.get_by_id(contact.id)
        assert reloaded is not None
        assert reloaded.is_primary is False


class TestEmergencyContactPrimaryUniqueness:
    async def test_two_primary_emergency_contacts_for_the_same_patient_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        patient = await persist_patient(db_session)
        repo = SqlAlchemyEmergencyContactRepository(db_session)

        first = EmergencyContact.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            full_name="John Doe",
            relationship="Spouse",
            phone_number=PhoneNumber("+1 555 0100"),
            is_primary=True,
        )
        await repo.add(first)
        await db_session.commit()

        second = EmergencyContact.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            full_name="Jane Smith",
            relationship="Sister",
            phone_number=PhoneNumber("+1 555 0200"),
            is_primary=True,
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestEmergencyContactRequiresValidPatient:
    async def test_nonexistent_patient_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization = (await persist_patient(db_session)).organization_id
        repo = SqlAlchemyEmergencyContactRepository(db_session)

        contact = EmergencyContact.create(
            organization_id=organization,
            patient_id=uuid4(),
            full_name="John Doe",
            relationship="Spouse",
            phone_number=PhoneNumber("+1 555 0100"),
        )
        await repo.add(contact)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
