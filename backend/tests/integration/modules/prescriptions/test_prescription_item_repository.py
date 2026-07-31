"""Integration tests for `SqlAlchemyPrescriptionItemRepository`, including
the FK to `prescriptions` and `list_by_prescription` ordering, against a
real PostgreSQL instance.

No soft-delete test here — unlike every other repository test in this
codebase, `prescription_items` carries no `deleted_at` column at all (see
`app/modules/prescriptions/infrastructure/models.py` for why)."""

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.prescriptions._helpers import persist_full_chain

from app.modules.prescriptions.domain.entities import Prescription, PrescriptionItem
from app.modules.prescriptions.domain.enums import AdministrationRoute
from app.modules.prescriptions.infrastructure.repositories import (
    SqlAlchemyPrescriptionItemRepository,
    SqlAlchemyPrescriptionRepository,
)


async def _persist_prescription(db_session: AsyncSession) -> Prescription:
    organization, patient, doctor, visit, clinical_note = await persist_full_chain(db_session)
    repo = SqlAlchemyPrescriptionRepository(db_session)
    prescription = Prescription.create(
        organization_id=organization.id,
        clinical_note_id=clinical_note.id,
        patient_id=patient.id,
        visit_id=visit.id,
        doctor_id=doctor.id,
        prescription_number=f"RX-{uuid4().hex[:12].upper()}",
        prescription_date=date(2026, 1, 1),
    )
    await repo.add(prescription)
    await db_session.commit()
    return prescription


class TestPrescriptionItemRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        prescription = await _persist_prescription(db_session)
        repo = SqlAlchemyPrescriptionItemRepository(db_session)

        item = PrescriptionItem.create(
            prescription_id=prescription.id,
            medication_name="Amoxicillin",
            generic_name="Amoxicillin trihydrate",
            strength="500mg",
            dosage="1",
            dosage_unit="tablet",
            frequency="three times daily",
            route=AdministrationRoute.ORAL,
            duration="7",
            duration_unit="days",
            quantity="21",
            instructions="Take with food",
        )
        await repo.add(item)
        await db_session.commit()

        reloaded = await repo.get_by_id(item.id)
        assert reloaded is not None
        assert reloaded.prescription_id == prescription.id
        assert reloaded.medication_name == "Amoxicillin"
        assert reloaded.generic_name == "Amoxicillin trihydrate"
        assert reloaded.strength == "500mg"
        assert reloaded.dosage == "1"
        assert reloaded.dosage_unit == "tablet"
        assert reloaded.frequency == "three times daily"
        assert reloaded.route is AdministrationRoute.ORAL
        assert reloaded.duration == "7"
        assert reloaded.duration_unit == "days"
        assert reloaded.quantity == "21"
        assert reloaded.instructions == "Take with food"

    async def test_save_with_nullable_fields_omitted(self, db_session: AsyncSession) -> None:
        prescription = await _persist_prescription(db_session)
        repo = SqlAlchemyPrescriptionItemRepository(db_session)

        item = PrescriptionItem.create(
            prescription_id=prescription.id,
            medication_name="Paracetamol",
            strength="500mg",
            dosage="2",
            dosage_unit="tablet",
            frequency="every 6 hours as needed",
            route=AdministrationRoute.ORAL,
            duration="5",
            duration_unit="days",
            quantity="20",
        )
        await repo.add(item)
        await db_session.commit()

        reloaded = await repo.get_by_id(item.id)
        assert reloaded is not None
        assert reloaded.generic_name is None
        assert reloaded.instructions is None

    async def test_every_administration_route_round_trips(self, db_session: AsyncSession) -> None:
        prescription = await _persist_prescription(db_session)
        repo = SqlAlchemyPrescriptionItemRepository(db_session)

        for route in AdministrationRoute:
            item = PrescriptionItem.create(
                prescription_id=prescription.id,
                medication_name=f"Medication for {route.value}",
                strength="10mg",
                dosage="1",
                dosage_unit="unit",
                frequency="once daily",
                route=route,
                duration="1",
                duration_unit="day",
                quantity="1",
            )
            await repo.add(item)
        await db_session.commit()

        items = await repo.list_by_prescription(prescription.id)
        assert {i.route for i in items} == set(AdministrationRoute)


class TestListByPrescription:
    async def test_returns_items_scoped_to_the_prescription(self, db_session: AsyncSession) -> None:
        prescription_a = await _persist_prescription(db_session)
        prescription_b = await _persist_prescription(db_session)
        repo = SqlAlchemyPrescriptionItemRepository(db_session)

        await repo.add(
            PrescriptionItem.create(
                prescription_id=prescription_a.id,
                medication_name="Amoxicillin",
                strength="500mg",
                dosage="1",
                dosage_unit="tablet",
                frequency="three times daily",
                route=AdministrationRoute.ORAL,
                duration="7",
                duration_unit="days",
                quantity="21",
            )
        )
        await repo.add(
            PrescriptionItem.create(
                prescription_id=prescription_b.id,
                medication_name="Ibuprofen",
                strength="200mg",
                dosage="2",
                dosage_unit="tablet",
                frequency="twice daily",
                route=AdministrationRoute.ORAL,
                duration="5",
                duration_unit="days",
                quantity="20",
            )
        )
        await db_session.commit()

        items = await repo.list_by_prescription(prescription_a.id)
        assert [i.medication_name for i in items] == ["Amoxicillin"]

    async def test_returns_empty_list_for_a_prescription_without_items(
        self, db_session: AsyncSession
    ) -> None:
        prescription = await _persist_prescription(db_session)
        repo = SqlAlchemyPrescriptionItemRepository(db_session)
        assert await repo.list_by_prescription(prescription.id) == []


class TestListByPrescriptions:
    """Search & Filtering module —
    `SqlAlchemyPrescriptionItemRepository.list_by_prescriptions`: the
    batch variant `PrescriptionQueryService.search_prescriptions` uses to
    avoid an N+1 query per result row."""

    async def test_returns_items_grouped_across_multiple_prescriptions_in_one_query(
        self, db_session: AsyncSession
    ) -> None:
        prescription_a = await _persist_prescription(db_session)
        prescription_b = await _persist_prescription(db_session)
        prescription_c = await _persist_prescription(db_session)
        repo = SqlAlchemyPrescriptionItemRepository(db_session)

        await repo.add(
            PrescriptionItem.create(
                prescription_id=prescription_a.id,
                medication_name="Amoxicillin",
                strength="500mg",
                dosage="1",
                dosage_unit="tablet",
                frequency="three times daily",
                route=AdministrationRoute.ORAL,
                duration="7",
                duration_unit="days",
                quantity="21",
            )
        )
        await repo.add(
            PrescriptionItem.create(
                prescription_id=prescription_b.id,
                medication_name="Ibuprofen",
                strength="200mg",
                dosage="2",
                dosage_unit="tablet",
                frequency="twice daily",
                route=AdministrationRoute.ORAL,
                duration="5",
                duration_unit="days",
                quantity="20",
            )
        )
        await db_session.commit()

        items = await repo.list_by_prescriptions([prescription_a.id, prescription_b.id])

        assert {i.medication_name for i in items} == {"Amoxicillin", "Ibuprofen"}
        assert all(i.prescription_id != prescription_c.id for i in items)

    async def test_returns_empty_list_for_no_prescription_ids(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyPrescriptionItemRepository(db_session)
        assert await repo.list_by_prescriptions([]) == []


class TestPrescriptionItemRequiresValidReference:
    async def test_nonexistent_prescription_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyPrescriptionItemRepository(db_session)

        item = PrescriptionItem.create(
            prescription_id=uuid4(),
            medication_name="Orphan Medication",
            strength="10mg",
            dosage="1",
            dosage_unit="tablet",
            frequency="once daily",
            route=AdministrationRoute.ORAL,
            duration="1",
            duration_unit="day",
            quantity="1",
        )
        await repo.add(item)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
