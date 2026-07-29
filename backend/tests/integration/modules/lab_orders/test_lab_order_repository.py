"""Integration tests for `SqlAlchemyLabOrderRepository`, including the FKs
to `organizations`/`clinical_notes`/`patients`/`patient_visits`/`doctors`,
the "order_number is globally unique" partial unique index, and — unlike
`soap_notes`/`prescriptions` — the *absence* of any one-to-one uniqueness
constraint on `clinical_note_id` ("One Clinical Note may contain multiple
Lab Orders"), against a real PostgreSQL instance.

No `TestCheckConstraints` class here, matching
`tests.integration.modules.prescriptions.test_prescription_repository` —
like `prescriptions`, `lab_orders` carries no `CHECK` constraints at all
(see `app/modules/lab_orders/infrastructure/models.py` for why "Ordered
Lab Orders must contain at least one Lab Order Item" has no
database-level enforcement layer)."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.lab_orders._helpers import (
    persist_clinical_note,
    persist_full_chain,
    persist_visit,
)

from app.modules.lab_orders.domain.entities import LabOrder
from app.modules.lab_orders.domain.enums import LabOrderStatus, Priority
from app.modules.lab_orders.infrastructure.repositories import SqlAlchemyLabOrderRepository


class TestLabOrderRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemyLabOrderRepository(db_session)

        lab_order = LabOrder.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            order_number="LAB-0001",
            ordered_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
            priority=Priority.STAT,
            clinical_information="Suspected infection",
            notes="Draw before antibiotics",
        )
        await repo.add(lab_order)
        await db_session.commit()

        reloaded = await repo.get_by_id(lab_order.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.clinical_note_id == clinical_note.id
        assert reloaded.patient_id == patient.id
        assert reloaded.visit_id == visit.id
        assert reloaded.doctor_id == doctor.id
        assert reloaded.order_number == "LAB-0001"
        assert reloaded.ordered_at == datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
        assert reloaded.priority is Priority.STAT
        assert reloaded.status is LabOrderStatus.DRAFT
        assert reloaded.clinical_information == "Suspected infection"
        assert reloaded.notes == "Draw before antibiotics"

    async def test_full_status_lifecycle_persists(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemyLabOrderRepository(db_session)

        lab_order = LabOrder.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            order_number="LAB-0002",
            ordered_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        await repo.add(lab_order)
        await db_session.commit()

        lab_order.place_order()
        await repo.add(lab_order)
        await db_session.commit()

        lab_order.mark_collected()
        await repo.add(lab_order)
        await db_session.commit()

        reloaded = await repo.get_by_id(lab_order.id)
        assert reloaded is not None
        assert reloaded.status is LabOrderStatus.COLLECTED

    async def test_cancellation_persists(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemyLabOrderRepository(db_session)

        lab_order = LabOrder.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            order_number="LAB-0003",
            ordered_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        await repo.add(lab_order)
        await db_session.commit()

        lab_order.cancel()
        await repo.add(lab_order)
        await db_session.commit()

        reloaded = await repo.get_by_id(lab_order.id)
        assert reloaded is not None
        assert reloaded.status is LabOrderStatus.CANCELLED


class TestGetByOrderNumber:
    async def test_returns_the_matching_lab_order(self, db_session: AsyncSession) -> None:
        organization, patient, doctor, visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemyLabOrderRepository(db_session)

        lab_order = LabOrder.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            order_number="LAB-UNIQUE",
            ordered_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        await repo.add(lab_order)
        await db_session.commit()

        found = await repo.get_by_order_number("LAB-UNIQUE")
        assert found is not None and found.id == lab_order.id

    async def test_returns_none_for_an_unknown_number(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyLabOrderRepository(db_session)
        assert await repo.get_by_order_number("does-not-exist") is None


class TestListByClinicalNote:
    async def test_multiple_lab_orders_for_the_same_clinical_note_are_all_returned(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemyLabOrderRepository(db_session)

        await repo.add(
            LabOrder.create(
                organization_id=organization.id,
                clinical_note_id=clinical_note.id,
                patient_id=patient.id,
                visit_id=visit.id,
                doctor_id=doctor.id,
                order_number="LAB-NOTE-A",
                ordered_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
            )
        )
        await repo.add(
            LabOrder.create(
                organization_id=organization.id,
                clinical_note_id=clinical_note.id,
                patient_id=patient.id,
                visit_id=visit.id,
                doctor_id=doctor.id,
                order_number="LAB-NOTE-B",
                ordered_at=datetime(2026, 1, 1, 9, 5, tzinfo=UTC),
            )
        )
        await db_session.commit()

        orders = await repo.list_by_clinical_note(clinical_note.id)
        assert {o.order_number for o in orders} == {"LAB-NOTE-A", "LAB-NOTE-B"}

    async def test_returns_empty_list_for_a_clinical_note_without_orders(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyLabOrderRepository(db_session)
        assert await repo.list_by_clinical_note(uuid4()) == []


class TestListByPatient:
    async def test_returns_orders_scoped_to_the_patient_across_visits(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit_a, clinical_note_a = await persist_full_chain(
            db_session
        )
        visit_b = await persist_visit(
            db_session, organization_id=organization.id, patient_id=patient.id, doctor_id=doctor.id
        )
        clinical_note_b = await persist_clinical_note(
            db_session,
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit_b.id,
            doctor_id=doctor.id,
        )
        _other_org, other_patient, other_doctor, other_visit, other_note = await persist_full_chain(
            db_session
        )
        repo = SqlAlchemyLabOrderRepository(db_session)

        await repo.add(
            LabOrder.create(
                organization_id=organization.id,
                clinical_note_id=clinical_note_a.id,
                patient_id=patient.id,
                visit_id=visit_a.id,
                doctor_id=doctor.id,
                order_number="LAB-PAT-A",
                ordered_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
            )
        )
        await repo.add(
            LabOrder.create(
                organization_id=organization.id,
                clinical_note_id=clinical_note_b.id,
                patient_id=patient.id,
                visit_id=visit_b.id,
                doctor_id=doctor.id,
                order_number="LAB-PAT-B",
                ordered_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
            )
        )
        await repo.add(
            LabOrder.create(
                organization_id=_other_org.id,
                clinical_note_id=other_note.id,
                patient_id=other_patient.id,
                visit_id=other_visit.id,
                doctor_id=other_doctor.id,
                order_number="LAB-PAT-OTHER",
                ordered_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
            )
        )
        await db_session.commit()

        orders = await repo.list_by_patient(patient.id)
        assert {o.order_number for o in orders} == {"LAB-PAT-A", "LAB-PAT-B"}


class TestOrderNumberUniqueness:
    async def test_duplicate_order_number_across_different_notes_violates_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit_a, clinical_note_a = await persist_full_chain(
            db_session
        )
        visit_b = await persist_visit(
            db_session, organization_id=organization.id, patient_id=patient.id, doctor_id=doctor.id
        )
        clinical_note_b = await persist_clinical_note(
            db_session,
            organization_id=organization.id,
            patient_id=patient.id,
            visit_id=visit_b.id,
            doctor_id=doctor.id,
        )
        repo = SqlAlchemyLabOrderRepository(db_session)
        shared_number = "LAB-SHARED"

        first = LabOrder.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note_a.id,
            patient_id=patient.id,
            visit_id=visit_a.id,
            doctor_id=doctor.id,
            order_number=shared_number,
            ordered_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        await repo.add(first)
        await db_session.commit()

        second = LabOrder.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note_b.id,
            patient_id=patient.id,
            visit_id=visit_b.id,
            doctor_id=doctor.id,
            order_number=shared_number,
            ordered_at=datetime(2026, 1, 1, 9, 5, tzinfo=UTC),
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestLabOrderRequiresValidReferences:
    async def test_nonexistent_organization_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        _organization, patient, doctor, visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemyLabOrderRepository(db_session)

        lab_order = LabOrder.create(
            organization_id=uuid4(),
            clinical_note_id=clinical_note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            order_number="LAB-ORPHAN-ORG",
            ordered_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        await repo.add(lab_order)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_clinical_note_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, visit, _clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemyLabOrderRepository(db_session)

        lab_order = LabOrder.create(
            organization_id=organization.id,
            clinical_note_id=uuid4(),
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=doctor.id,
            order_number="LAB-ORPHAN-NOTE",
            ordered_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        await repo.add(lab_order)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_patient_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _patient, doctor, visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemyLabOrderRepository(db_session)

        lab_order = LabOrder.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note.id,
            patient_id=uuid4(),
            visit_id=visit.id,
            doctor_id=doctor.id,
            order_number="LAB-ORPHAN-PATIENT",
            ordered_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        await repo.add(lab_order)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_visit_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, doctor, _visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemyLabOrderRepository(db_session)

        lab_order = LabOrder.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note.id,
            patient_id=patient.id,
            visit_id=uuid4(),
            doctor_id=doctor.id,
            order_number="LAB-ORPHAN-VISIT",
            ordered_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        await repo.add(lab_order)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_doctor_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, patient, _doctor, visit, clinical_note = await persist_full_chain(db_session)
        repo = SqlAlchemyLabOrderRepository(db_session)

        lab_order = LabOrder.create(
            organization_id=organization.id,
            clinical_note_id=clinical_note.id,
            patient_id=patient.id,
            visit_id=visit.id,
            doctor_id=uuid4(),
            order_number="LAB-ORPHAN-DOCTOR",
            ordered_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        await repo.add(lab_order)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
