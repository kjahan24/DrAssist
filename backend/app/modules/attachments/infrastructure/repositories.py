"""Concrete SQLAlchemy repository implementation.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — see the identical pattern (and rationale) in
`app.modules.procedures.infrastructure.repositories`.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.attachments.domain.entities import VisitAttachment
from app.modules.attachments.domain.repositories import VisitAttachmentRepository
from app.modules.attachments.domain.value_objects import Sha256Checksum
from app.modules.attachments.infrastructure.mappers import (
    apply_visit_attachment_to_model,
    visit_attachment_to_domain,
)
from app.modules.attachments.infrastructure.models import VisitAttachmentModel


class SqlAlchemyVisitAttachmentRepository(VisitAttachmentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, attachment_id: UUID) -> VisitAttachment | None:
        model = await self._session.get(VisitAttachmentModel, attachment_id)
        if model is None or model.deleted_at is not None:
            return None
        return visit_attachment_to_domain(model)

    async def get_by_storage_key(self, storage_key: str) -> VisitAttachment | None:
        stmt = select(VisitAttachmentModel).where(
            VisitAttachmentModel.storage_key == storage_key.strip(),
            VisitAttachmentModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return visit_attachment_to_domain(model) if model is not None else None

    async def get_by_checksum(self, checksum: Sha256Checksum) -> VisitAttachment | None:
        stmt = select(VisitAttachmentModel).where(
            VisitAttachmentModel.checksum_sha256 == str(checksum),
            VisitAttachmentModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return visit_attachment_to_domain(model) if model is not None else None

    async def list_by_visit(self, visit_id: UUID) -> list[VisitAttachment]:
        stmt = (
            select(VisitAttachmentModel)
            .where(
                VisitAttachmentModel.visit_id == visit_id,
                VisitAttachmentModel.deleted_at.is_(None),
            )
            .order_by(VisitAttachmentModel.uploaded_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [visit_attachment_to_domain(model) for model in models]

    async def add(self, attachment: VisitAttachment) -> None:
        model = await self._session.get(VisitAttachmentModel, attachment.id)
        if model is None:
            model = VisitAttachmentModel()
            self._session.add(model)
        apply_visit_attachment_to_model(attachment, model)
