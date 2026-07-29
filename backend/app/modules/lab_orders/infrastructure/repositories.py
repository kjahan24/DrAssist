"""Concrete SQLAlchemy repository implementations.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — see the identical pattern (and rationale) in
`app.modules.prescriptions.infrastructure.repositories`.

Neither repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.lab_orders.domain.entities import LabOrder, LabOrderItem
from app.modules.lab_orders.domain.repositories import LabOrderItemRepository, LabOrderRepository
from app.modules.lab_orders.infrastructure.mappers import (
    apply_lab_order_item_to_model,
    apply_lab_order_to_model,
    lab_order_item_to_domain,
    lab_order_to_domain,
)
from app.modules.lab_orders.infrastructure.models import LabOrderItemModel, LabOrderModel


class SqlAlchemyLabOrderRepository(LabOrderRepository):
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

    async def add(self, item: LabOrderItem) -> None:
        model = await self._session.get(LabOrderItemModel, item.id)
        if model is None:
            model = LabOrderItemModel()
            self._session.add(model)
        apply_lab_order_item_to_model(item, model)
