"""Integration tests for `SqlAlchemyLabResultItemRepository`, including
the FKs to `lab_results` and `lab_order_items` (the latter backing "Every
Lab Result Item must reference an existing Lab Order Item") and
`list_by_lab_result` ordering, against a real PostgreSQL instance.

No soft-delete test here — unlike every other repository test in this
codebase, `lab_result_items` carries no `deleted_at` column at all (see
`app/modules/lab_results/infrastructure/models.py` for why)."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.lab_results._helpers import persist_full_chain

from app.modules.lab_results.domain.entities import LabResult, LabResultItem
from app.modules.lab_results.domain.enums import AbnormalFlag
from app.modules.lab_results.infrastructure.repositories import (
    SqlAlchemyLabResultItemRepository,
    SqlAlchemyLabResultRepository,
)


async def _persist_lab_result(db_session: AsyncSession) -> tuple[LabResult, object]:
    (
        organization,
        patient,
        doctor,
        visit,
        _note,
        lab_order,
        lab_order_item,
    ) = await persist_full_chain(db_session)
    repo = SqlAlchemyLabResultRepository(db_session)
    lab_result = LabResult.create(
        organization_id=organization.id,
        lab_order_id=lab_order.id,
        patient_id=patient.id,
        visit_id=visit.id,
        doctor_id=doctor.id,
        result_number=f"RES-{uuid4().hex[:12].upper()}",
        reported_at=datetime(2026, 1, 2, 8, 0, tzinfo=UTC),
    )
    await repo.add(lab_result)
    await db_session.commit()
    return lab_result, lab_order_item


class TestLabResultItemRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        lab_result, lab_order_item = await _persist_lab_result(db_session)
        repo = SqlAlchemyLabResultItemRepository(db_session)

        item = LabResultItem.create(
            lab_result_id=lab_result.id,
            lab_order_item_id=lab_order_item.id,  # type: ignore[attr-defined]
            test_code="CBC",
            test_name="Complete Blood Count",
            result_value="5.4",
            result_unit="x10^9/L",
            reference_range="4.0-11.0 x10^9/L",
            abnormal_flag=AbnormalFlag.NORMAL,
            interpretation="Within normal limits",
        )
        await repo.add(item)
        await db_session.commit()

        reloaded = await repo.get_by_id(item.id)
        assert reloaded is not None
        assert reloaded.lab_result_id == lab_result.id
        assert reloaded.lab_order_item_id == lab_order_item.id  # type: ignore[attr-defined]
        assert reloaded.test_code == "CBC"
        assert reloaded.test_name == "Complete Blood Count"
        assert reloaded.result_value == "5.4"
        assert reloaded.result_unit == "x10^9/L"
        assert reloaded.reference_range == "4.0-11.0 x10^9/L"
        assert reloaded.abnormal_flag is AbnormalFlag.NORMAL
        assert reloaded.interpretation == "Within normal limits"

    async def test_save_with_nullable_fields_omitted(self, db_session: AsyncSession) -> None:
        lab_result, lab_order_item = await _persist_lab_result(db_session)
        repo = SqlAlchemyLabResultItemRepository(db_session)

        item = LabResultItem.create(
            lab_result_id=lab_result.id,
            lab_order_item_id=lab_order_item.id,  # type: ignore[attr-defined]
            test_code="CBC",
            test_name="Complete Blood Count",
            result_value="5.4",
            abnormal_flag=AbnormalFlag.NORMAL,
        )
        await repo.add(item)
        await db_session.commit()

        reloaded = await repo.get_by_id(item.id)
        assert reloaded is not None
        assert reloaded.result_unit is None
        assert reloaded.reference_range is None
        assert reloaded.interpretation is None

    async def test_every_abnormal_flag_round_trips(self, db_session: AsyncSession) -> None:
        lab_result, lab_order_item = await _persist_lab_result(db_session)
        repo = SqlAlchemyLabResultItemRepository(db_session)

        for flag in AbnormalFlag:
            item = LabResultItem.create(
                lab_result_id=lab_result.id,
                lab_order_item_id=lab_order_item.id,  # type: ignore[attr-defined]
                test_code=f"CODE-{flag.value}",
                test_name=f"Test for {flag.value}",
                result_value="1",
                abnormal_flag=flag,
            )
            await repo.add(item)
        await db_session.commit()

        items = await repo.list_by_lab_result(lab_result.id)
        assert {i.abnormal_flag for i in items} == set(AbnormalFlag)


class TestListByLabResult:
    async def test_returns_items_scoped_to_the_lab_result(self, db_session: AsyncSession) -> None:
        lab_result_a, lab_order_item_a = await _persist_lab_result(db_session)
        lab_result_b, lab_order_item_b = await _persist_lab_result(db_session)
        repo = SqlAlchemyLabResultItemRepository(db_session)

        await repo.add(
            LabResultItem.create(
                lab_result_id=lab_result_a.id,
                lab_order_item_id=lab_order_item_a.id,  # type: ignore[attr-defined]
                test_code="CBC",
                test_name="Complete Blood Count",
                result_value="5.4",
                abnormal_flag=AbnormalFlag.NORMAL,
            )
        )
        await repo.add(
            LabResultItem.create(
                lab_result_id=lab_result_b.id,
                lab_order_item_id=lab_order_item_b.id,  # type: ignore[attr-defined]
                test_code="HGB",
                test_name="Hemoglobin",
                result_value="9.8",
                abnormal_flag=AbnormalFlag.LOW,
            )
        )
        await db_session.commit()

        items = await repo.list_by_lab_result(lab_result_a.id)
        assert [i.test_name for i in items] == ["Complete Blood Count"]

    async def test_returns_empty_list_for_a_lab_result_without_items(
        self, db_session: AsyncSession
    ) -> None:
        lab_result, _lab_order_item = await _persist_lab_result(db_session)
        repo = SqlAlchemyLabResultItemRepository(db_session)
        assert await repo.list_by_lab_result(lab_result.id) == []


class TestListByLabResults:
    """Search & Filtering module —
    `SqlAlchemyLabResultItemRepository.list_by_lab_results`: the batch
    variant `LabResultQueryService.search_lab_results` uses to avoid an
    N+1 query per result row."""

    async def test_returns_items_grouped_across_multiple_lab_results_in_one_query(
        self, db_session: AsyncSession
    ) -> None:
        lab_result_a, lab_order_item_a = await _persist_lab_result(db_session)
        lab_result_b, lab_order_item_b = await _persist_lab_result(db_session)
        repo = SqlAlchemyLabResultItemRepository(db_session)

        await repo.add(
            LabResultItem.create(
                lab_result_id=lab_result_a.id,
                lab_order_item_id=lab_order_item_a.id,  # type: ignore[attr-defined]
                test_code="CBC",
                test_name="Complete Blood Count",
                result_value="5.4",
                abnormal_flag=AbnormalFlag.NORMAL,
            )
        )
        await repo.add(
            LabResultItem.create(
                lab_result_id=lab_result_b.id,
                lab_order_item_id=lab_order_item_b.id,  # type: ignore[attr-defined]
                test_code="HGB",
                test_name="Hemoglobin",
                result_value="9.8",
                abnormal_flag=AbnormalFlag.LOW,
            )
        )
        await db_session.commit()

        items = await repo.list_by_lab_results([lab_result_a.id, lab_result_b.id])

        assert {i.test_name for i in items} == {"Complete Blood Count", "Hemoglobin"}

    async def test_returns_empty_list_for_no_lab_result_ids(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyLabResultItemRepository(db_session)
        assert await repo.list_by_lab_results([]) == []


class TestLabResultItemRequiresValidReferences:
    async def test_nonexistent_lab_result_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        _lab_result, lab_order_item = await _persist_lab_result(db_session)
        repo = SqlAlchemyLabResultItemRepository(db_session)

        item = LabResultItem.create(
            lab_result_id=uuid4(),
            lab_order_item_id=lab_order_item.id,  # type: ignore[attr-defined]
            test_code="ORPHAN",
            test_name="Orphan Result",
            result_value="1",
            abnormal_flag=AbnormalFlag.NORMAL,
        )
        await repo.add(item)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_nonexistent_lab_order_item_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        lab_result, _lab_order_item = await _persist_lab_result(db_session)
        repo = SqlAlchemyLabResultItemRepository(db_session)

        item = LabResultItem.create(
            lab_result_id=lab_result.id,
            lab_order_item_id=uuid4(),
            test_code="ORPHAN",
            test_name="Orphan Result",
            result_value="1",
            abnormal_flag=AbnormalFlag.NORMAL,
        )
        await repo.add(item)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_another_lab_order_item_from_a_different_chain_still_satisfies_the_fk(
        self, db_session: AsyncSession
    ) -> None:
        """The FK only requires the referenced row to exist somewhere in
        `lab_order_items` — cross-lab-order consistency ("this item must
        belong to *this* lab result's own lab order") is a business rule
        enforced by `AddLabResultItem` at the application layer, not by
        the database (a `CHECK`/FK cannot express "belongs to the same
        parent as a sibling row"); see `domain/entities.py`."""
        lab_result, _own_item = await _persist_lab_result(db_session)
        _other_result, other_lab_order_item = await _persist_lab_result(db_session)
        repo = SqlAlchemyLabResultItemRepository(db_session)

        item = LabResultItem.create(
            lab_result_id=lab_result.id,
            lab_order_item_id=other_lab_order_item.id,  # type: ignore[attr-defined]
            test_code="CROSS",
            test_name="Cross Chain Result",
            result_value="1",
            abnormal_flag=AbnormalFlag.NORMAL,
        )
        await repo.add(item)
        await db_session.commit()

        reloaded = await repo.get_by_id(item.id)
        assert reloaded is not None
