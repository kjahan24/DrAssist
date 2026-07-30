"""Concrete SQLAlchemy repository implementation.

`add()` is "upsert" in shape (look up by id, create if missing, then
overwrite mapped columns) purely for consistency with every other
repository in this codebase — see the identical pattern in
`app.modules.icd10_coding.infrastructure.repositories`. In practice this
module's own use case never calls `add()` on a row that already exists
("History records are immutable"): it is only ever exercised as an
insert.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.patient_history.domain.entities import PatientHistory
from app.modules.patient_history.domain.enums import ReferenceType
from app.modules.patient_history.domain.repositories import PatientHistoryRepository
from app.modules.patient_history.infrastructure.mappers import (
    apply_patient_history_to_model,
    patient_history_to_domain,
)
from app.modules.patient_history.infrastructure.models import PatientHistoryModel


class SqlAlchemyPatientHistoryRepository(PatientHistoryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, patient_history_id: UUID) -> PatientHistory | None:
        model = await self._session.get(PatientHistoryModel, patient_history_id)
        if model is None or model.deleted_at is not None:
            return None
        return patient_history_to_domain(model)

    async def get_by_reference(
        self, reference_type: ReferenceType, reference_id: UUID
    ) -> PatientHistory | None:
        stmt = select(PatientHistoryModel).where(
            PatientHistoryModel.reference_type == reference_type,
            PatientHistoryModel.reference_id == reference_id,
            PatientHistoryModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return patient_history_to_domain(model) if model is not None else None

    async def list_by_patient(self, patient_id: UUID) -> list[PatientHistory]:
        stmt = (
            select(PatientHistoryModel)
            .where(
                PatientHistoryModel.patient_id == patient_id,
                PatientHistoryModel.deleted_at.is_(None),
            )
            .order_by(PatientHistoryModel.encounter_date)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [patient_history_to_domain(model) for model in models]

    async def list_by_visit(self, visit_id: UUID) -> list[PatientHistory]:
        stmt = (
            select(PatientHistoryModel)
            .where(
                PatientHistoryModel.visit_id == visit_id,
                PatientHistoryModel.deleted_at.is_(None),
            )
            .order_by(PatientHistoryModel.encounter_date)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [patient_history_to_domain(model) for model in models]

    async def add(self, history: PatientHistory) -> None:
        model = await self._session.get(PatientHistoryModel, history.id)
        if model is None:
            model = PatientHistoryModel()
            self._session.add(model)
        apply_patient_history_to_model(history, model)
