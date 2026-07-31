"""Concrete SQLAlchemy repository implementations.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — see the identical pattern (and rationale) in
`app.modules.soap_notes.infrastructure.repositories`.

Neither repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from collections.abc import Sequence
from datetime import date, datetime
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
from app.modules.prescriptions.domain.entities import Prescription, PrescriptionItem
from app.modules.prescriptions.domain.enums import PrescriptionStatus
from app.modules.prescriptions.domain.repositories import (
    PrescriptionItemRepository,
    PrescriptionRepository,
)
from app.modules.prescriptions.infrastructure.mappers import (
    apply_prescription_item_to_model,
    apply_prescription_to_model,
    prescription_item_to_domain,
    prescription_to_domain,
)
from app.modules.prescriptions.infrastructure.models import PrescriptionItemModel, PrescriptionModel


class SqlAlchemyPrescriptionRepository(PrescriptionRepository):
    _SORT_COLUMNS: dict[str, InstrumentedAttribute[Any]] = {
        "created_at": PrescriptionModel.created_at,
        "updated_at": PrescriptionModel.updated_at,
        "prescription_number": PrescriptionModel.prescription_number,
        "prescription_date": PrescriptionModel.prescription_date,
        "status": PrescriptionModel.status,
    }

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, prescription_id: UUID) -> Prescription | None:
        model = await self._session.get(PrescriptionModel, prescription_id)
        if model is None or model.deleted_at is not None:
            return None
        return prescription_to_domain(model)

    async def get_by_clinical_note_id(self, clinical_note_id: UUID) -> Prescription | None:
        stmt = select(PrescriptionModel).where(
            PrescriptionModel.clinical_note_id == clinical_note_id,
            PrescriptionModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return prescription_to_domain(model) if model is not None else None

    async def get_by_prescription_number(self, prescription_number: str) -> Prescription | None:
        stmt = select(PrescriptionModel).where(
            PrescriptionModel.prescription_number == prescription_number.strip(),
            PrescriptionModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return prescription_to_domain(model) if model is not None else None

    async def list_by_patient(self, patient_id: UUID) -> list[Prescription]:
        stmt = (
            select(PrescriptionModel)
            .where(
                PrescriptionModel.patient_id == patient_id,
                PrescriptionModel.deleted_at.is_(None),
            )
            .order_by(PrescriptionModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [prescription_to_domain(model) for model in models]

    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        statuses: Sequence[PrescriptionStatus] | None = None,
        patient_id: UUID | None = None,
        doctor_id: UUID | None = None,
        visit_id: UUID | None = None,
        prescription_date_from: date | None = None,
        prescription_date_to: date | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Prescription], int]:
        stmt = select(PrescriptionModel)
        stmt = scope_to_organization(stmt, PrescriptionModel.organization_id, organization_id)
        stmt = exclude_soft_deleted(
            stmt, PrescriptionModel.deleted_at, include_deleted=include_deleted
        )
        stmt = apply_equality(stmt, PrescriptionModel.patient_id, patient_id)
        stmt = apply_equality(stmt, PrescriptionModel.doctor_id, doctor_id)
        stmt = apply_equality(stmt, PrescriptionModel.visit_id, visit_id)
        stmt = apply_in_filter(stmt, PrescriptionModel.status, statuses)
        stmt = apply_date_range(
            stmt,
            PrescriptionModel.prescription_date,
            start=prescription_date_from,
            end=prescription_date_to,
        )
        stmt = apply_date_range(
            stmt, PrescriptionModel.created_at, start=created_from, end=created_to
        )
        stmt = apply_date_range(
            stmt, PrescriptionModel.updated_at, start=updated_from, end=updated_to
        )
        stmt = apply_combined_text_search(
            stmt,
            full_text_columns=[PrescriptionModel.notes],
            partial_columns=[PrescriptionModel.prescription_number],
            term=query,
        )

        total = await count_total(self._session, stmt)
        column = self._SORT_COLUMNS.get(sort_by, PrescriptionModel.created_at)
        stmt = apply_sort(stmt, column, sort_order)
        stmt = apply_pagination(stmt, offset=offset, limit=limit)
        models = (await self._session.execute(stmt)).scalars().all()
        return [prescription_to_domain(model) for model in models], total

    async def add(self, prescription: Prescription) -> None:
        model = await self._session.get(PrescriptionModel, prescription.id)
        if model is None:
            model = PrescriptionModel()
            self._session.add(model)
        apply_prescription_to_model(prescription, model)


class SqlAlchemyPrescriptionItemRepository(PrescriptionItemRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, prescription_item_id: UUID) -> PrescriptionItem | None:
        model = await self._session.get(PrescriptionItemModel, prescription_item_id)
        return prescription_item_to_domain(model) if model is not None else None

    async def list_by_prescription(self, prescription_id: UUID) -> list[PrescriptionItem]:
        stmt = (
            select(PrescriptionItemModel)
            .where(PrescriptionItemModel.prescription_id == prescription_id)
            .order_by(PrescriptionItemModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [prescription_item_to_domain(model) for model in models]

    async def list_by_prescriptions(
        self, prescription_ids: Sequence[UUID]
    ) -> list[PrescriptionItem]:
        if not prescription_ids:
            return []
        stmt = (
            select(PrescriptionItemModel)
            .where(PrescriptionItemModel.prescription_id.in_(prescription_ids))
            .order_by(PrescriptionItemModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [prescription_item_to_domain(model) for model in models]

    async def add(self, item: PrescriptionItem) -> None:
        model = await self._session.get(PrescriptionItemModel, item.id)
        if model is None:
            model = PrescriptionItemModel()
            self._session.add(model)
        apply_prescription_item_to_model(item, model)
