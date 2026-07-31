"""Concrete SQLAlchemy repository implementation.

`add()` is "upsert" in shape (look up by id, create if missing, then
overwrite mapped columns) purely for consistency with every other
repository in this codebase — see the identical pattern in
`app.modules.icd10_coding.infrastructure.repositories`. In practice this
module's own use case never calls `add()` on a row that already exists
("History records are immutable"): it is only ever exercised as an
insert.

No repository calls `session.commit()` — that is exclusively the
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
    apply_date_range,
    apply_equality,
    apply_full_text_search,
    apply_in_filter,
    apply_pagination,
    apply_sort,
    count_total,
    exclude_soft_deleted,
    scope_to_organization,
)
from app.modules.patient_history.domain.entities import PatientHistory
from app.modules.patient_history.domain.enums import HistoryType, ReferenceType
from app.modules.patient_history.domain.repositories import PatientHistoryRepository
from app.modules.patient_history.infrastructure.mappers import (
    apply_patient_history_to_model,
    patient_history_to_domain,
)
from app.modules.patient_history.infrastructure.models import PatientHistoryModel


class SqlAlchemyPatientHistoryRepository(PatientHistoryRepository):
    _SORT_COLUMNS: dict[str, InstrumentedAttribute[Any]] = {
        "created_at": PatientHistoryModel.created_at,
        "updated_at": PatientHistoryModel.updated_at,
        "encounter_date": PatientHistoryModel.encounter_date,
        "history_type": PatientHistoryModel.history_type,
        "reference_type": PatientHistoryModel.reference_type,
    }

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, patient_history_id: UUID) -> PatientHistory | None:
        model = await self._session.get(PatientHistoryModel, patient_history_id)
        if model is None or model.deleted_at is not None:
            return None
        return patient_history_to_domain(model)

    async def get_by_reference(
        self, reference_type: ReferenceType, reference_id: UUID
    ) -> PatientHistory | None:
        stmt = select(PatientHistoryModel).where(
            PatientHistoryModel.reference_type == reference_type,
            PatientHistoryModel.reference_id == reference_id,
            PatientHistoryModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return patient_history_to_domain(model) if model is not None else None

    async def list_by_patient(self, patient_id: UUID) -> list[PatientHistory]:
        stmt = (
            select(PatientHistoryModel)
            .where(
                PatientHistoryModel.patient_id == patient_id,
                PatientHistoryModel.deleted_at.is_(None),
            )
            .order_by(PatientHistoryModel.encounter_date)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [patient_history_to_domain(model) for model in models]

    async def list_by_visit(self, visit_id: UUID) -> list[PatientHistory]:
        stmt = (
            select(PatientHistoryModel)
            .where(
                PatientHistoryModel.visit_id == visit_id,
                PatientHistoryModel.deleted_at.is_(None),
            )
            .order_by(PatientHistoryModel.encounter_date)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [patient_history_to_domain(model) for model in models]

    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        history_types: Sequence[HistoryType] | None = None,
        reference_types: Sequence[ReferenceType] | None = None,
        patient_id: UUID | None = None,
        visit_id: UUID | None = None,
        doctor_review_id: UUID | None = None,
        reference_id: UUID | None = None,
        encounter_date_from: date | None = None,
        encounter_date_to: date | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "encounter_date",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[PatientHistory], int]:
        stmt = select(PatientHistoryModel)
        stmt = scope_to_organization(stmt, PatientHistoryModel.organization_id, organization_id)
        stmt = exclude_soft_deleted(
            stmt, PatientHistoryModel.deleted_at, include_deleted=include_deleted
        )
        stmt = apply_equality(stmt, PatientHistoryModel.patient_id, patient_id)
        stmt = apply_equality(stmt, PatientHistoryModel.visit_id, visit_id)
        stmt = apply_equality(stmt, PatientHistoryModel.doctor_review_id, doctor_review_id)
        stmt = apply_equality(stmt, PatientHistoryModel.reference_id, reference_id)
        stmt = apply_in_filter(stmt, PatientHistoryModel.history_type, history_types)
        stmt = apply_in_filter(stmt, PatientHistoryModel.reference_type, reference_types)
        stmt = apply_date_range(
            stmt,
            PatientHistoryModel.encounter_date,
            start=encounter_date_from,
            end=encounter_date_to,
        )
        stmt = apply_date_range(
            stmt, PatientHistoryModel.created_at, start=created_from, end=created_to
        )
        stmt = apply_date_range(
            stmt, PatientHistoryModel.updated_at, start=updated_from, end=updated_to
        )
        stmt = apply_full_text_search(stmt, [PatientHistoryModel.summary], query)

        total = await count_total(self._session, stmt)
        column = self._SORT_COLUMNS.get(sort_by, PatientHistoryModel.encounter_date)
        stmt = apply_sort(stmt, column, sort_order)
        stmt = apply_pagination(stmt, offset=offset, limit=limit)
        models = (await self._session.execute(stmt)).scalars().all()
        return [patient_history_to_domain(model) for model in models], total

    async def add(self, history: PatientHistory) -> None:
        model = await self._session.get(PatientHistoryModel, history.id)
        if model is None:
            model = PatientHistoryModel()
            self._session.add(model)
        apply_patient_history_to_model(history, model)
