"""Concrete SQLAlchemy repository implementation.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — see the identical pattern (and rationale) in
`app.modules.attachments.infrastructure.repositories`.

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
    apply_in_filter,
    apply_pagination,
    apply_sort,
    count_total,
    exclude_soft_deleted,
    scope_to_organization,
)
from app.modules.clinical_notes.domain.entities import ClinicalNote
from app.modules.clinical_notes.domain.enums import ClinicalNoteStatus
from app.modules.clinical_notes.domain.repositories import ClinicalNoteRepository
from app.modules.clinical_notes.infrastructure.mappers import (
    apply_clinical_note_to_model,
    clinical_note_to_domain,
)
from app.modules.clinical_notes.infrastructure.models import ClinicalNoteModel


class SqlAlchemyClinicalNoteRepository(ClinicalNoteRepository):
    _SORT_COLUMNS: dict[str, InstrumentedAttribute[Any]] = {
        "created_at": ClinicalNoteModel.created_at,
        "updated_at": ClinicalNoteModel.updated_at,
        "note_number": ClinicalNoteModel.note_number,
        "note_type": ClinicalNoteModel.note_type,
        "status": ClinicalNoteModel.status,
        "encounter_datetime": ClinicalNoteModel.encounter_datetime,
    }

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, clinical_note_id: UUID) -> ClinicalNote | None:
        model = await self._session.get(ClinicalNoteModel, clinical_note_id)
        if model is None or model.deleted_at is not None:
            return None
        return clinical_note_to_domain(model)

    async def get_by_note_number(self, note_number: str) -> ClinicalNote | None:
        stmt = select(ClinicalNoteModel).where(
            ClinicalNoteModel.note_number == note_number.strip(),
            ClinicalNoteModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return clinical_note_to_domain(model) if model is not None else None

    async def list_by_visit(self, visit_id: UUID) -> list[ClinicalNote]:
        stmt = (
            select(ClinicalNoteModel)
            .where(
                ClinicalNoteModel.visit_id == visit_id,
                ClinicalNoteModel.deleted_at.is_(None),
            )
            .order_by(ClinicalNoteModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [clinical_note_to_domain(model) for model in models]

    async def list_by_patient(self, patient_id: UUID) -> list[ClinicalNote]:
        stmt = (
            select(ClinicalNoteModel)
            .where(
                ClinicalNoteModel.patient_id == patient_id,
                ClinicalNoteModel.deleted_at.is_(None),
            )
            .order_by(ClinicalNoteModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [clinical_note_to_domain(model) for model in models]

    async def search(
        self,
        *,
        organization_id: UUID,
        query: str | None = None,
        statuses: Sequence[ClinicalNoteStatus] | None = None,
        patient_id: UUID | None = None,
        doctor_id: UUID | None = None,
        visit_id: UUID | None = None,
        encounter_from: datetime | None = None,
        encounter_to: datetime | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        include_deleted: bool = False,
        sort_by: str = "encounter_datetime",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[ClinicalNote], int]:
        stmt = select(ClinicalNoteModel)
        stmt = scope_to_organization(stmt, ClinicalNoteModel.organization_id, organization_id)
        stmt = exclude_soft_deleted(
            stmt, ClinicalNoteModel.deleted_at, include_deleted=include_deleted
        )
        stmt = apply_equality(stmt, ClinicalNoteModel.patient_id, patient_id)
        stmt = apply_equality(stmt, ClinicalNoteModel.doctor_id, doctor_id)
        stmt = apply_equality(stmt, ClinicalNoteModel.visit_id, visit_id)
        stmt = apply_in_filter(stmt, ClinicalNoteModel.status, statuses)
        stmt = apply_date_range(
            stmt, ClinicalNoteModel.encounter_datetime, start=encounter_from, end=encounter_to
        )
        stmt = apply_date_range(
            stmt, ClinicalNoteModel.created_at, start=created_from, end=created_to
        )
        stmt = apply_date_range(
            stmt, ClinicalNoteModel.updated_at, start=updated_from, end=updated_to
        )
        stmt = apply_combined_text_search(
            stmt,
            full_text_columns=[
                ClinicalNoteModel.chief_complaint_summary,
                ClinicalNoteModel.history_summary,
                ClinicalNoteModel.examination_summary,
                ClinicalNoteModel.assessment_summary,
                ClinicalNoteModel.plan_summary,
            ],
            partial_columns=[ClinicalNoteModel.note_number],
            term=query,
        )

        total = await count_total(self._session, stmt)
        column = self._SORT_COLUMNS.get(sort_by, ClinicalNoteModel.encounter_datetime)
        stmt = apply_sort(stmt, column, sort_order)
        stmt = apply_pagination(stmt, offset=offset, limit=limit)
        models = (await self._session.execute(stmt)).scalars().all()
        return [clinical_note_to_domain(model) for model in models], total

    async def add(self, clinical_note: ClinicalNote) -> None:
        model = await self._session.get(ClinicalNoteModel, clinical_note.id)
        if model is None:
            model = ClinicalNoteModel()
            self._session.add(model)
        apply_clinical_note_to_model(clinical_note, model)
