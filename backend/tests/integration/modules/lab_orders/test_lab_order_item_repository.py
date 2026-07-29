"""Integration tests for `SqlAlchemyLabOrderItemRepository`, including the
FK to `lab_orders` and `list_by_lab_order` ordering, against a real
PostgreSQL instance.

No soft-delete test here — unlike every other repository test in this
codebase, `lab_order_items` carries no `deleted_at` column at all (see
`app/modules/lab_orders/infrastructure/models.py` for why)."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.lab_orders._helpers import persist_full_chain

from app.modules.lab_orders.domain.entities import LabOrder, LabOrderItem
from app.modules.lab_orders.domain.enums import LabOrderStatus
from app.modules.lab_orders.infrastructure.repositories import (
    SqlAlchemyLabOrderItemRepository,
    SqlAlchemyLabOrderRepository,
)


async def _persist_lab_order(db_session: AsyncSession) -> LabOrder:
    organization, patient, doctor, visit, clinical_note = await persist_full_chain(db_session)
    repo = SqlAlchemyLabOrderRepository(db_session)
    lab_order = LabOrder.create(
        organization_id=organization.id,
        clinical_note_id=clinical_note.id,
        patient_id=patient.id,
        visit_id=visit.id,
        doctor_id=doctor.id,
        order_number=f"LAB-{uuid4().hex[:12].upper()}",
        ordered_at=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
    )
    await repo.add(lab_order)
    await db_session.commit()
    return lab_order


class TestLabOrderItemRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        lab_order = await _persist_lab_order(db_session)
        repo = SqlAlchemyLabOrderItemRepository(db_session)

        item = LabOrderItem.create(
            lab_order_id=lab_order.id,
            test_code="CBC",
            test_name="Complete Blood Count",
            specimen_type="Blood",
            specimen_site="Left arm",
            instructions="Fasting not required",
        )
        await repo.add(item)
        await db_session.commit()

        reloaded = await repo.get_by_id(item.id)
        assert reloaded is not None
        assert reloaded.lab_order_id == lab_order.id
        assert reloaded.test_code == "CBC"
        assert reloaded.test_name == "Complete Blood Count"
        assert reloaded.specimen_type == "Blood"
        assert reloaded.specimen_site == "Left arm"
        assert reloaded.status is LabOrderStatus.DRAFT
        assert reloaded.instructions == "Fasting not required"

    async def test_save_with_nullable_fields_omitted(self, db_session: AsyncSession) -> None:
        lab_order = await _persist_lab_order(db_session)
        repo = SqlAlchemyLabOrderItemRepository(db_session)

        item = LabOrderItem.create(
            lab_order_id=lab_order.id,
            test_code="URIN",
            test_name="Urinalysis",
            specimen_type="Urine",
        )
        await repo.add(item)
        await db_session.commit()

        reloaded = await repo.get_by_id(item.id)
        assert reloaded is not None
        assert reloaded.specimen_site is None
        assert reloaded.instructions is None


class TestListByLabOrder:
    async def test_returns_items_scoped_to_the_lab_order(self, db_session: AsyncSession) -> None:
        lab_order_a = await _persist_lab_order(db_session)
        lab_order_b = await _persist_lab_order(db_session)
        repo = SqlAlchemyLabOrderItemRepository(db_session)

        await repo.add(
            LabOrderItem.create(
                lab_order_id=lab_order_a.id,
                test_code="CBC",
                test_name="Complete Blood Count",
                specimen_type="Blood",
            )
        )
        await repo.add(
            LabOrderItem.create(
                lab_order_id=lab_order_b.id,
                test_code="URIN",
                test_name="Urinalysis",
                specimen_type="Urine",
            )
        )
        await db_session.commit()

        items = await repo.list_by_lab_order(lab_order_a.id)
        assert [i.test_name for i in items] == ["Complete Blood Count"]

    async def test_returns_empty_list_for_a_lab_order_without_items(
        self, db_session: AsyncSession
    ) -> None:
        lab_order = await _persist_lab_order(db_session)
        repo = SqlAlchemyLabOrderItemRepository(db_session)
        assert await repo.list_by_lab_order(lab_order.id) == []


class TestLabOrderItemRequiresValidReference:
    async def test_nonexistent_lab_order_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyLabOrderItemRepository(db_session)

        item = LabOrderItem.create(
            lab_order_id=uuid4(),
            test_code="ORPHAN",
            test_name="Orphan Test",
            specimen_type="Blood",
        )
        await repo.add(item)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
