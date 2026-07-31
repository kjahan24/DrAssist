"""Concrete SQLAlchemy repository implementation.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — the identical pattern (and rationale) in
`app.modules.attachments.infrastructure.repositories`.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.documents.domain.entities import MedicalDocument
from app.modules.documents.domain.repositories import MedicalDocumentRepository
from app.modules.documents.infrastructure.mappers import (
    apply_medical_document_to_model,
    medical_document_to_domain,
)
from app.modules.documents.infrastructure.models import MedicalDocumentModel


class SqlAlchemyMedicalDocumentRepository(MedicalDocumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, document_id: UUID) -> MedicalDocument | None:
        model = await self._session.get(MedicalDocumentModel, document_id)
        if model is None or model.deleted_at is not None:
            return None
        return medical_document_to_domain(model)

    async def get_by_stored_filename(self, stored_filename: str) -> MedicalDocument | None:
        stmt = select(MedicalDocumentModel).where(
            MedicalDocumentModel.stored_filename == stored_filename.strip(),
            MedicalDocumentModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return medical_document_to_domain(model) if model is not None else None

    async def list_by_patient(self, patient_id: UUID) -> list[MedicalDocument]:
        stmt = (
            select(MedicalDocumentModel)
            .where(
                MedicalDocumentModel.patient_id == patient_id,
                MedicalDocumentModel.deleted_at.is_(None),
            )
            .order_by(MedicalDocumentModel.uploaded_at.desc())
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [medical_document_to_domain(model) for model in models]

    async def list_by_visit(self, visit_id: UUID) -> list[MedicalDocument]:
        stmt = (
            select(MedicalDocumentModel)
            .where(
                MedicalDocumentModel.visit_id == visit_id,
                MedicalDocumentModel.deleted_at.is_(None),
            )
            .order_by(MedicalDocumentModel.uploaded_at.desc())
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [medical_document_to_domain(model) for model in models]

    async def list_by_appointment(self, appointment_id: UUID) -> list[MedicalDocument]:
        stmt = (
            select(MedicalDocumentModel)
            .where(
                MedicalDocumentModel.appointment_id == appointment_id,
                MedicalDocumentModel.deleted_at.is_(None),
            )
            .order_by(MedicalDocumentModel.uploaded_at.desc())
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [medical_document_to_domain(model) for model in models]

    async def add(self, document: MedicalDocument) -> None:
        model = await self._session.get(MedicalDocumentModel, document.id)
        if model is None:
            model = MedicalDocumentModel()
            self._session.add(model)
        apply_medical_document_to_model(document, model)
