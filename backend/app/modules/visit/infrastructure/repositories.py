"""Concrete SQLAlchemy repository implementation.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — see the identical pattern (and rationale) in
`app.modules.doctor.infrastructure.repositories`.

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
from app.modules.visit.domain.entities import PatientVisit
from app.modules.visit.domain.enums import VisitStatus
from app.modules.visit.domain.repositories import PatientVisitRepository
from app.modules.visit.infrastructure.mappers import (
    apply_patient_visit_to_model,
    patient_visit_to_domain,
)
from app.modules.visit.infrastructure.models import PatientVisitModel


class SqlAlchemyPatientVisitRepository(PatientVisitRepository):
    _SORT_COLUMNS: dict[str, InstrumentedAttribute[Any]] = {
        "created_at": PatientVisitModel.created_at,
        "updated_at": PatientVisitModel.updated_at,
        "visit_date": PatientVisitModel.visit_date,
        "visit_number": PatientVisitModel.visit_number,
        "visit_status": PatientVisitModel.visit_status,
    }

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, visit_id: UUID) -> PatientVisit | None:
        model = await self._session.get(PatientVisitModel, visit_id)
        if model is None or model.deleted_at is not None:
            return None
        return patient_visit_to_domain(model)

    async def get_by_visit_number(
        self, *, organization_id: UUID, visit_number: str
    ) -> PatientVisit | None:
        stmt = select(PatientVisitModel).where(
            PatientVisitModel.organization_id == organization_id,
            PatientVisitModel.visit_number == visit_number.strip(),
            PatientVisitModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return patient_visit_to_domain(model) if model is not None else None

    async def list_by_patient(self, patient_id: UUID) -> list[PatientVisit]:
        stmt = (
            select(PatientVisitModel)
            .where(
                PatientVisitModel.patient_id == patient_id,
                PatientVisitModel.deleted_at.is_(None),
            )
            .order_by(PatientVisitModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [patient_visit_to_domain(model) for model in models]

    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        statuses: Sequence[VisitStatus] | None = None,
        patient_id: UUID | None = None,
        doctor_id: UUID | None = None,
        visit_date_from: date | None = None,
        visit_date_to: date | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "visit_date",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[PatientVisit], int]:
        stmt = select(PatientVisitModel)
        stmt = scope_to_organization(stmt, PatientVisitModel.organization_id, organization_id)
        stmt = exclude_soft_deleted(
            stmt, PatientVisitModel.deleted_at, include_deleted=include_deleted
        )
        stmt = apply_equality(stmt, PatientVisitModel.patient_id, patient_id)
        stmt = apply_equality(stmt, PatientVisitModel.doctor_id, doctor_id)
        stmt = apply_in_filter(stmt, PatientVisitModel.visit_status, statuses)
        stmt = apply_date_range(
            stmt, PatientVisitModel.visit_date, start=visit_date_from, end=visit_date_to
        )
        stmt = apply_date_range(
            stmt, PatientVisitModel.created_at, start=created_from, end=created_to
        )
        stmt = apply_date_range(
            stmt, PatientVisitModel.updated_at, start=updated_from, end=updated_to
        )
        stmt = apply_combined_text_search(
            stmt,
            full_text_columns=[
                PatientVisitModel.chief_complaint_summary,
                PatientVisitModel.reason_for_visit,
                PatientVisitModel.notes,
            ],
            partial_columns=[PatientVisitModel.visit_number],
            term=query,
        )

        total = await count_total(self._session, stmt)
        column = self._SORT_COLUMNS.get(sort_by, PatientVisitModel.visit_date)
        stmt = apply_sort(stmt, column, sort_order)
        stmt = apply_pagination(stmt, offset=offset, limit=limit)
        models = (await self._session.execute(stmt)).scalars().all()
        return [patient_visit_to_domain(model) for model in models], total

    async def add(self, visit: PatientVisit) -> None:
        model = await self._session.get(PatientVisitModel, visit.id)
        if model is None:
            model = PatientVisitModel()
            self._session.add(model)
        apply_patient_visit_to_model(visit, model)
