"""Concrete SQLAlchemy repository implementation.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — see the identical pattern (and rationale) in
`app.modules.visit.infrastructure.repositories`.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vital_signs.domain.entities import VisitVitalSigns
from app.modules.vital_signs.domain.repositories import VisitVitalSignsRepository
from app.modules.vital_signs.infrastructure.mappers import (
    apply_visit_vital_signs_to_model,
    visit_vital_signs_to_domain,
)
from app.modules.vital_signs.infrastructure.models import VisitVitalSignsModel


class SqlAlchemyVisitVitalSignsRepository(VisitVitalSignsRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, vital_signs_id: UUID) -> VisitVitalSigns | None:
        model = await self._session.get(VisitVitalSignsModel, vital_signs_id)
        if model is None or model.deleted_at is not None:
            return None
        return visit_vital_signs_to_domain(model)

    async def get_by_visit_id(self, visit_id: UUID) -> VisitVitalSigns | None:
        stmt = select(VisitVitalSignsModel).where(
            VisitVitalSignsModel.visit_id == visit_id,
            VisitVitalSignsModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return visit_vital_signs_to_domain(model) if model is not None else None

    async def add(self, vital_signs: VisitVitalSigns) -> None:
        model = await self._session.get(VisitVitalSignsModel, vital_signs.id)
        if model is None:
            model = VisitVitalSignsModel()
            self._session.add(model)
        apply_visit_vital_signs_to_model(vital_signs, model)
