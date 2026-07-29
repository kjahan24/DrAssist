"""Concrete SQLAlchemy repository implementation.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — see the identical pattern (and rationale) in
`app.modules.lab_orders.infrastructure.repositories`.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.clinical_reasoning.domain.entities import ClinicalReasoning
from app.modules.clinical_reasoning.domain.repositories import ClinicalReasoningRepository
from app.modules.clinical_reasoning.infrastructure.mappers import (
    apply_clinical_reasoning_to_model,
    clinical_reasoning_to_domain,
)
from app.modules.clinical_reasoning.infrastructure.models import ClinicalReasoningModel


class SqlAlchemyClinicalReasoningRepository(ClinicalReasoningRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, clinical_reasoning_id: UUID) -> ClinicalReasoning | None:
        model = await self._session.get(ClinicalReasoningModel, clinical_reasoning_id)
        if model is None or model.deleted_at is not None:
            return None
        return clinical_reasoning_to_domain(model)

    async def list_by_clinical_note(self, clinical_note_id: UUID) -> list[ClinicalReasoning]:
        stmt = (
            select(ClinicalReasoningModel)
            .where(
                ClinicalReasoningModel.clinical_note_id == clinical_note_id,
                ClinicalReasoningModel.deleted_at.is_(None),
            )
            .order_by(ClinicalReasoningModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [clinical_reasoning_to_domain(model) for model in models]

    async def list_by_patient(self, patient_id: UUID) -> list[ClinicalReasoning]:
        stmt = (
            select(ClinicalReasoningModel)
            .where(
                ClinicalReasoningModel.patient_id == patient_id,
                ClinicalReasoningModel.deleted_at.is_(None),
            )
            .order_by(ClinicalReasoningModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [clinical_reasoning_to_domain(model) for model in models]

    async def add(self, reasoning: ClinicalReasoning) -> None:
        model = await self._session.get(ClinicalReasoningModel, reasoning.id)
        if model is None:
            model = ClinicalReasoningModel()
            self._session.add(model)
        apply_clinical_reasoning_to_model(reasoning, model)
