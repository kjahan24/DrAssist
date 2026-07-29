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

from app.modules.lab_results.domain.entities import LabResult, LabResultItem
from app.modules.lab_results.domain.repositories import (
    LabResultItemRepository,
    LabResultRepository,
)
from app.modules.lab_results.infrastructure.mappers import (
    apply_lab_result_item_to_model,
    apply_lab_result_to_model,
    lab_result_item_to_domain,
    lab_result_to_domain,
)
from app.modules.lab_results.infrastructure.models import LabResultItemModel, LabResultModel


class SqlAlchemyLabResultRepository(LabResultRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, lab_result_id: UUID) -> LabResult | None:
        model = await self._session.get(LabResultModel, lab_result_id)
        if model is None or model.deleted_at is not None:
            return None
        return lab_result_to_domain(model)

    async def get_by_lab_order_id(self, lab_order_id: UUID) -> LabResult | None:
        stmt = select(LabResultModel).where(
            LabResultModel.lab_order_id == lab_order_id,
            LabResultModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return lab_result_to_domain(model) if model is not None else None

    async def get_by_result_number(self, result_number: str) -> LabResult | None:
        stmt = select(LabResultModel).where(
            LabResultModel.result_number == result_number.strip(),
            LabResultModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return lab_result_to_domain(model) if model is not None else None

    async def list_by_patient(self, patient_id: UUID) -> list[LabResult]:
        stmt = (
            select(LabResultModel)
            .where(
                LabResultModel.patient_id == patient_id,
                LabResultModel.deleted_at.is_(None),
            )
            .order_by(LabResultModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [lab_result_to_domain(model) for model in models]

    async def add(self, lab_result: LabResult) -> None:
        model = await self._session.get(LabResultModel, lab_result.id)
        if model is None:
            model = LabResultModel()
            self._session.add(model)
        apply_lab_result_to_model(lab_result, model)


class SqlAlchemyLabResultItemRepository(LabResultItemRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, lab_result_item_id: UUID) -> LabResultItem | None:
        model = await self._session.get(LabResultItemModel, lab_result_item_id)
        return lab_result_item_to_domain(model) if model is not None else None

    async def list_by_lab_result(self, lab_result_id: UUID) -> list[LabResultItem]:
        stmt = (
            select(LabResultItemModel)
            .where(LabResultItemModel.lab_result_id == lab_result_id)
            .order_by(LabResultItemModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [lab_result_item_to_domain(model) for model in models]

    async def add(self, item: LabResultItem) -> None:
        model = await self._session.get(LabResultItemModel, item.id)
        if model is None:
            model = LabResultItemModel()
            self._session.add(model)
        apply_lab_result_item_to_model(item, model)
