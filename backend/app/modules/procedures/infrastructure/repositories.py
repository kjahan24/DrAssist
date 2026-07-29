"""Concrete SQLAlchemy repository implementation.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — see the identical pattern (and rationale) in
`app.modules.diagnosis.infrastructure.repositories`.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.procedures.domain.entities import VisitProcedure
from app.modules.procedures.domain.repositories import VisitProcedureRepository
from app.modules.procedures.infrastructure.mappers import (
    apply_visit_procedure_to_model,
    visit_procedure_to_domain,
)
from app.modules.procedures.infrastructure.models import VisitProcedureModel


class SqlAlchemyVisitProcedureRepository(VisitProcedureRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, procedure_id: UUID) -> VisitProcedure | None:
        model = await self._session.get(VisitProcedureModel, procedure_id)
        if model is None or model.deleted_at is not None:
            return None
        return visit_procedure_to_domain(model)

    async def get_by_visit_and_sequence(
        self, *, visit_id: UUID, sequence_number: int
    ) -> VisitProcedure | None:
        stmt = select(VisitProcedureModel).where(
            VisitProcedureModel.visit_id == visit_id,
            VisitProcedureModel.sequence_number == sequence_number,
            VisitProcedureModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return visit_procedure_to_domain(model) if model is not None else None

    async def list_by_visit(self, visit_id: UUID) -> list[VisitProcedure]:
        stmt = (
            select(VisitProcedureModel)
            .where(
                VisitProcedureModel.visit_id == visit_id,
                VisitProcedureModel.deleted_at.is_(None),
            )
            .order_by(VisitProcedureModel.sequence_number)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [visit_procedure_to_domain(model) for model in models]

    async def add(self, procedure: VisitProcedure) -> None:
        model = await self._session.get(VisitProcedureModel, procedure.id)
        if model is None:
            model = VisitProcedureModel()
            self._session.add(model)
        apply_visit_procedure_to_model(procedure, model)
