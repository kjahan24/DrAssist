"""Concrete SQLAlchemy repository implementation.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — see the identical pattern (and rationale) in
`app.modules.vital_signs.infrastructure.repositories`.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.soap_notes.domain.entities import SOAPNote
from app.modules.soap_notes.domain.repositories import SOAPNoteRepository
from app.modules.soap_notes.infrastructure.mappers import (
    apply_soap_note_to_model,
    soap_note_to_domain,
)
from app.modules.soap_notes.infrastructure.models import SOAPNoteModel


class SqlAlchemySOAPNoteRepository(SOAPNoteRepository):
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

    async def add(self, soap_note: SOAPNote) -> None:
        model = await self._session.get(SOAPNoteModel, soap_note.id)
        if model is None:
            model = SOAPNoteModel()
            self._session.add(model)
        apply_soap_note_to_model(soap_note, model)
