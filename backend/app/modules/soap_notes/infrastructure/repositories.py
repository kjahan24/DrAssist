"""Concrete SQLAlchemy repository implementation.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — see the identical pattern (and rationale) in
`app.modules.vital_signs.infrastructure.repositories`.

No repository calls `session.commit()` — that is exclusively the
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
    apply_pagination,
    apply_sort,
    count_total,
    exclude_soft_deleted,
    scope_to_organization,
)
from app.modules.soap_notes.domain.entities import SOAPNote
from app.modules.soap_notes.domain.repositories import SOAPNoteRepository
from app.modules.soap_notes.infrastructure.mappers import (
    apply_soap_note_to_model,
    soap_note_to_domain,
)
from app.modules.soap_notes.infrastructure.models import SOAPNoteModel


class SqlAlchemySOAPNoteRepository(SOAPNoteRepository):
    _SORT_COLUMNS: dict[str, InstrumentedAttribute[Any]] = {
        "created_at": SOAPNoteModel.created_at,
        "updated_at": SOAPNoteModel.updated_at,
    }

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, soap_note_id: UUID) -> SOAPNote | None:
        model = await self._session.get(SOAPNoteModel, soap_note_id)
        if model is None or model.deleted_at is not None:
            return None
        return soap_note_to_domain(model)

    async def get_by_clinical_note_id(self, clinical_note_id: UUID) -> SOAPNote | None:
        stmt = select(SOAPNoteModel).where(
            SOAPNoteModel.clinical_note_id == clinical_note_id,
            SOAPNoteModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return soap_note_to_domain(model) if model is not None else None

    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        patient_id: UUID | None = None,
        doctor_id: UUID | None = None,
        visit_id: UUID | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[SOAPNote], int]:
        stmt = select(SOAPNoteModel)
        stmt = scope_to_organization(stmt, SOAPNoteModel.organization_id, organization_id)
        stmt = exclude_soft_deleted(stmt, SOAPNoteModel.deleted_at, include_deleted=include_deleted)
        stmt = apply_equality(stmt, SOAPNoteModel.patient_id, patient_id)
        stmt = apply_equality(stmt, SOAPNoteModel.doctor_id, doctor_id)
        stmt = apply_equality(stmt, SOAPNoteModel.visit_id, visit_id)
        stmt = apply_date_range(stmt, SOAPNoteModel.created_at, start=created_from, end=created_to)
        stmt = apply_date_range(stmt, SOAPNoteModel.updated_at, start=updated_from, end=updated_to)
        stmt = apply_combined_text_search(
            stmt,
            full_text_columns=[
                SOAPNoteModel.chief_complaint,
                SOAPNoteModel.history_of_present_illness,
                SOAPNoteModel.review_of_systems,
                SOAPNoteModel.physical_examination,
                SOAPNoteModel.assessment,
                SOAPNoteModel.plan,
            ],
            term=query,
        )

        total = await count_total(self._session, stmt)
        column = self._SORT_COLUMNS.get(sort_by, SOAPNoteModel.created_at)
        stmt = apply_sort(stmt, column, sort_order)
        stmt = apply_pagination(stmt, offset=offset, limit=limit)
        models = (await self._session.execute(stmt)).scalars().all()
        return [soap_note_to_domain(model) for model in models], total

    async def add(self, soap_note: SOAPNote) -> None:
        model = await self._session.get(SOAPNoteModel, soap_note.id)
        if model is None:
            model = SOAPNoteModel()
            self._session.add(model)
        apply_soap_note_to_model(soap_note, model)
