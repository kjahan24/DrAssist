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
from app.modules.lab_results.domain.entities import LabResult, LabResultItem
from app.modules.lab_results.domain.enums import LabResultStatus
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
    _SORT_COLUMNS: dict[str, InstrumentedAttribute[Any]] = {
        "created_at": LabResultModel.created_at,
        "updated_at": LabResultModel.updated_at,
        "result_number": LabResultModel.result_number,
        "reported_at": LabResultModel.reported_at,
        "status": LabResultModel.status,
    }

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

    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        statuses: Sequence[LabResultStatus] | None = None,
        patient_id: UUID | None = None,
        doctor_id: UUID | None = None,
        visit_id: UUID | None = None,
        lab_order_id: UUID | None = None,
        reported_from: datetime | None = None,
        reported_to: datetime | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "reported_at",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[LabResult], int]:
        stmt = select(LabResultModel)
        stmt = scope_to_organization(stmt, LabResultModel.organization_id, organization_id)
        stmt = exclude_soft_deleted(
            stmt, LabResultModel.deleted_at, include_deleted=include_deleted
        )
        stmt = apply_equality(stmt, LabResultModel.patient_id, patient_id)
        stmt = apply_equality(stmt, LabResultModel.doctor_id, doctor_id)
        stmt = apply_equality(stmt, LabResultModel.visit_id, visit_id)
        stmt = apply_equality(stmt, LabResultModel.lab_order_id, lab_order_id)
        stmt = apply_in_filter(stmt, LabResultModel.status, statuses)
        stmt = apply_date_range(
            stmt, LabResultModel.reported_at, start=reported_from, end=reported_to
        )
        stmt = apply_date_range(stmt, LabResultModel.created_at, start=created_from, end=created_to)
        stmt = apply_date_range(stmt, LabResultModel.updated_at, start=updated_from, end=updated_to)
        stmt = apply_combined_text_search(
            stmt,
            full_text_columns=[LabResultModel.laboratory_name, LabResultModel.comments],
            partial_columns=[LabResultModel.result_number],
            term=query,
        )

        total = await count_total(self._session, stmt)
        column = self._SORT_COLUMNS.get(sort_by, LabResultModel.reported_at)
        stmt = apply_sort(stmt, column, sort_order)
        stmt = apply_pagination(stmt, offset=offset, limit=limit)
        models = (await self._session.execute(stmt)).scalars().all()
        return [lab_result_to_domain(model) for model in models], total

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

    async def list_by_lab_results(self, lab_result_ids: Sequence[UUID]) -> list[LabResultItem]:
        if not lab_result_ids:
            return []
        stmt = (
            select(LabResultItemModel)
            .where(LabResultItemModel.lab_result_id.in_(lab_result_ids))
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
