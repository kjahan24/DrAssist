"""Concrete SQLAlchemy repository implementation.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — see the identical pattern (and rationale) in
`app.modules.doctor.infrastructure.repositories`.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.visit.domain.entities import PatientVisit
from app.modules.visit.domain.repositories import PatientVisitRepository
from app.modules.visit.infrastructure.mappers import (
    apply_patient_visit_to_model,
    patient_visit_to_domain,
)
from app.modules.visit.infrastructure.models import PatientVisitModel


class SqlAlchemyPatientVisitRepository(PatientVisitRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, visit_id: UUID) -> PatientVisit | None:
        model = await self._session.get(PatientVisitModel, visit_id)
        if model is None or model.deleted_at is not None:
            return None
        return patient_visit_to_domain(model)

    async def get_by_visit_number(
        self, *, organization_id: UUID, visit_number: str
    ) -> PatientVisit | None:
        stmt = select(PatientVisitModel).where(
            PatientVisitModel.organization_id == organization_id,
            PatientVisitModel.visit_number == visit_number.strip(),
            PatientVisitModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return patient_visit_to_domain(model) if model is not None else None

    async def list_by_patient(self, patient_id: UUID) -> list[PatientVisit]:
        stmt = (
            select(PatientVisitModel)
            .where(
                PatientVisitModel.patient_id == patient_id,
                PatientVisitModel.deleted_at.is_(None),
            )
            .order_by(PatientVisitModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [patient_visit_to_domain(model) for model in models]

    async def add(self, visit: PatientVisit) -> None:
        model = await self._session.get(PatientVisitModel, visit.id)
        if model is None:
            model = PatientVisitModel()
            self._session.add(model)
        apply_patient_visit_to_model(visit, model)
