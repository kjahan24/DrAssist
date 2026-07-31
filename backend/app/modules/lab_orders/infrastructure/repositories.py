"""Concrete SQLAlchemy repository implementations.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — see the identical pattern (and rationale) in
`app.modules.prescriptions.infrastructure.repositories`.

Neither repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.infrastructure.database.query_utils import (
    apply_combined_text_search,
    apply_date_range,
    apply_equality,
    apply_in_filter,
    apply_pagination,
    apply_sort,
    count_total,
    exclude_soft_deleted,
    scope_to_organization,
)
from app.modules.lab_orders.domain.entities import LabOrder, LabOrderItem
from app.modules.lab_orders.domain.enums import LabOrderStatus, Priority
from app.modules.lab_orders.domain.repositories import LabOrderItemRepository, LabOrderRepository
from app.modules.lab_orders.infrastructure.mappers import (
    apply_lab_order_item_to_model,
    apply_lab_order_to_model,
    lab_order_item_to_domain,
    lab_order_to_domain,
)
from app.modules.lab_orders.infrastructure.models import LabOrderItemModel, LabOrderModel


class SqlAlchemyLabOrderRepository(LabOrderRepository):
    _SORT_COLUMNS: dict[str, InstrumentedAttribute[Any]] = {
        "created_at": LabOrderModel.created_at,
        "updated_at": LabOrderModel.updated_at,
        "order_number": LabOrderModel.order_number,
        "ordered_at": LabOrderModel.ordered_at,
        "priority": LabOrderModel.priority,
        "status": LabOrderModel.status,
    }

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, lab_order_id: UUID) -> LabOrder | None:
        model = await self._session.get(LabOrderModel, lab_order_id)
        if model is None or model.deleted_at is not None:
            return None
        return lab_order_to_domain(model)

    async def get_by_order_number(self, order_number: str) -> LabOrder | None:
        stmt = select(LabOrderModel).where(
            LabOrderModel.order_number == order_number.strip(),
            LabOrderModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return lab_order_to_domain(model) if model is not None else None

    async def list_by_clinical_note(self, clinical_note_id: UUID) -> list[LabOrder]:
        stmt = (
            select(LabOrderModel)
            .where(
                LabOrderModel.clinical_note_id == clinical_note_id,
                LabOrderModel.deleted_at.is_(None),
            )
            .order_by(LabOrderModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [lab_order_to_domain(model) for model in models]

    async def list_by_patient(self, patient_id: UUID) -> list[LabOrder]:
        stmt = (
            select(LabOrderModel)
            .where(
                LabOrderModel.patient_id == patient_id,
                LabOrderModel.deleted_at.is_(None),
            )
            .order_by(LabOrderModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [lab_order_to_domain(model) for model in models]

    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        statuses: Sequence[LabOrderStatus] | None = None,
        priorities: Sequence[Priority] | None = None,
        patient_id: UUID | None = None,
        doctor_id: UUID | None = None,
        visit_id: UUID | None = None,
        clinical_note_id: UUID | None = None,
        ordered_from: datetime | None = None,
        ordered_to: datetime | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "ordered_at",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[LabOrder], int]:
        stmt = select(LabOrderModel)
        stmt = scope_to_organization(stmt, LabOrderModel.organization_id, organization_id)
        stmt = exclude_soft_deleted(stmt, LabOrderModel.deleted_at, include_deleted=include_deleted)
        stmt = apply_equality(stmt, LabOrderModel.patient_id, patient_id)
        stmt = apply_equality(stmt, LabOrderModel.doctor_id, doctor_id)
        stmt = apply_equality(stmt, LabOrderModel.visit_id, visit_id)
        stmt = apply_equality(stmt, LabOrderModel.clinical_note_id, clinical_note_id)
        stmt = apply_in_filter(stmt, LabOrderModel.status, statuses)
        stmt = apply_in_filter(stmt, LabOrderModel.priority, priorities)
        stmt = apply_date_range(stmt, LabOrderModel.ordered_at, start=ordered_from, end=ordered_to)
        stmt = apply_date_range(stmt, LabOrderModel.created_at, start=created_from, end=created_to)
        stmt = apply_date_range(stmt, LabOrderModel.updated_at, start=updated_from, end=updated_to)
        stmt = apply_combined_text_search(
            stmt,
            full_text_columns=[LabOrderModel.clinical_information, LabOrderModel.notes],
            partial_columns=[LabOrderModel.order_number],
            term=query,
        )

        total = await count_total(self._session, stmt)
        column = self._SORT_COLUMNS.get(sort_by, LabOrderModel.ordered_at)
        stmt = apply_sort(stmt, column, sort_order)
        stmt = apply_pagination(stmt, offset=offset, limit=limit)
        models = (await self._session.execute(stmt)).scalars().all()
        return [lab_order_to_domain(model) for model in models], total

    async def add(self, lab_order: LabOrder) -> None:
        model = await self._session.get(LabOrderModel, lab_order.id)
        if model is None:
            model = LabOrderModel()
            self._session.add(model)
        apply_lab_order_to_model(lab_order, model)


class SqlAlchemyLabOrderItemRepository(LabOrderItemRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, lab_order_item_id: UUID) -> LabOrderItem | None:
        model = await self._session.get(LabOrderItemModel, lab_order_item_id)
        return lab_order_item_to_domain(model) if model is not None else None

    async def list_by_lab_order(self, lab_order_id: UUID) -> list[LabOrderItem]:
        stmt = (
            select(LabOrderItemModel)
            .where(LabOrderItemModel.lab_order_id == lab_order_id)
            .order_by(LabOrderItemModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [lab_order_item_to_domain(model) for model in models]

    async def list_by_lab_orders(self, lab_order_ids: Sequence[UUID]) -> list[LabOrderItem]:
        if not lab_order_ids:
            return []
        stmt = (
            select(LabOrderItemModel)
            .where(LabOrderItemModel.lab_order_id.in_(lab_order_ids))
            .order_by(LabOrderItemModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [lab_order_item_to_domain(model) for model in models]

    async def add(self, item: LabOrderItem) -> None:
        model = await self._session.get(LabOrderItemModel, item.id)
        if model is None:
            model = LabOrderItemModel()
            self._session.add(model)
        apply_lab_order_item_to_model(item, model)
