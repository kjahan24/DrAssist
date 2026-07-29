"""Concrete SQLAlchemy repository implementation.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — see the identical pattern (and rationale) in
`app.modules.attachments.infrastructure.repositories`.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.clinical_notes.domain.entities import ClinicalNote
from app.modules.clinical_notes.domain.repositories import ClinicalNoteRepository
from app.modules.clinical_notes.infrastructure.mappers import (
    apply_clinical_note_to_model,
    clinical_note_to_domain,
)
from app.modules.clinical_notes.infrastructure.models import ClinicalNoteModel


class SqlAlchemyClinicalNoteRepository(ClinicalNoteRepository):
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

    async def add(self, clinical_note: ClinicalNote) -> None:
        model = await self._session.get(ClinicalNoteModel, clinical_note.id)
        if model is None:
            model = ClinicalNoteModel()
            self._session.add(model)
        apply_clinical_note_to_model(clinical_note, model)
