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

from app.modules.chief_complaints.domain.entities import VisitChiefComplaint
from app.modules.chief_complaints.domain.repositories import VisitChiefComplaintRepository
from app.modules.chief_complaints.infrastructure.mappers import (
    apply_visit_chief_complaint_to_model,
    visit_chief_complaint_to_domain,
)
from app.modules.chief_complaints.infrastructure.models import VisitChiefComplaintModel


class SqlAlchemyVisitChiefComplaintRepository(VisitChiefComplaintRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, chief_complaint_id: UUID) -> VisitChiefComplaint | None:
        model = await self._session.get(VisitChiefComplaintModel, chief_complaint_id)
        if model is None or model.deleted_at is not None:
            return None
        return visit_chief_complaint_to_domain(model)

    async def get_by_visit_and_sequence(
        self, *, visit_id: UUID, sequence_number: int
    ) -> VisitChiefComplaint | None:
        stmt = select(VisitChiefComplaintModel).where(
            VisitChiefComplaintModel.visit_id == visit_id,
            VisitChiefComplaintModel.sequence_number == sequence_number,
            VisitChiefComplaintModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return visit_chief_complaint_to_domain(model) if model is not None else None

    async def list_by_visit(self, visit_id: UUID) -> list[VisitChiefComplaint]:
        stmt = (
            select(VisitChiefComplaintModel)
            .where(
                VisitChiefComplaintModel.visit_id == visit_id,
                VisitChiefComplaintModel.deleted_at.is_(None),
            )
            .order_by(VisitChiefComplaintModel.sequence_number)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [visit_chief_complaint_to_domain(model) for model in models]

    async def add(self, chief_complaint: VisitChiefComplaint) -> None:
        model = await self._session.get(VisitChiefComplaintModel, chief_complaint.id)
        if model is None:
            model = VisitChiefComplaintModel()
            self._session.add(model)
        apply_visit_chief_complaint_to_model(chief_complaint, model)
