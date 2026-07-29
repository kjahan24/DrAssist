"""Concrete SQLAlchemy repository implementation.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — see the identical pattern (and rationale) in
`app.modules.chief_complaints.infrastructure.repositories`.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.diagnosis.domain.entities import VisitDiagnosis
from app.modules.diagnosis.domain.enums import DiagnosisType
from app.modules.diagnosis.domain.repositories import VisitDiagnosisRepository
from app.modules.diagnosis.infrastructure.mappers import (
    apply_visit_diagnosis_to_model,
    visit_diagnosis_to_domain,
)
from app.modules.diagnosis.infrastructure.models import VisitDiagnosisModel


class SqlAlchemyVisitDiagnosisRepository(VisitDiagnosisRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, diagnosis_id: UUID) -> VisitDiagnosis | None:
        model = await self._session.get(VisitDiagnosisModel, diagnosis_id)
        if model is None or model.deleted_at is not None:
            return None
        return visit_diagnosis_to_domain(model)

    async def get_by_visit_and_sequence(
        self, *, visit_id: UUID, sequence_number: int
    ) -> VisitDiagnosis | None:
        stmt = select(VisitDiagnosisModel).where(
            VisitDiagnosisModel.visit_id == visit_id,
            VisitDiagnosisModel.sequence_number == sequence_number,
            VisitDiagnosisModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return visit_diagnosis_to_domain(model) if model is not None else None

    async def get_primary_for_visit(self, visit_id: UUID) -> VisitDiagnosis | None:
        stmt = select(VisitDiagnosisModel).where(
            VisitDiagnosisModel.visit_id == visit_id,
            VisitDiagnosisModel.diagnosis_type == DiagnosisType.PRIMARY,
            VisitDiagnosisModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return visit_diagnosis_to_domain(model) if model is not None else None

    async def list_by_visit(self, visit_id: UUID) -> list[VisitDiagnosis]:
        stmt = (
            select(VisitDiagnosisModel)
            .where(
                VisitDiagnosisModel.visit_id == visit_id,
                VisitDiagnosisModel.deleted_at.is_(None),
            )
            .order_by(VisitDiagnosisModel.sequence_number)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [visit_diagnosis_to_domain(model) for model in models]

    async def add(self, diagnosis: VisitDiagnosis) -> None:
        model = await self._session.get(VisitDiagnosisModel, diagnosis.id)
        if model is None:
            model = VisitDiagnosisModel()
            self._session.add(model)
        apply_visit_diagnosis_to_model(diagnosis, model)
