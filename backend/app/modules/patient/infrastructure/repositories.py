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

from app.modules.patient.domain.entities import Patient
from app.modules.patient.domain.repositories import PatientRepository
from app.modules.patient.infrastructure.mappers import apply_patient_to_model, patient_to_domain
from app.modules.patient.infrastructure.models import PatientModel


class SqlAlchemyPatientRepository(PatientRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, patient_id: UUID) -> Patient | None:
        model = await self._session.get(PatientModel, patient_id)
        if model is None or model.deleted_at is not None:
            return None
        return patient_to_domain(model)

    async def get_by_patient_number(
        self, *, organization_id: UUID, patient_number: str
    ) -> Patient | None:
        stmt = select(PatientModel).where(
            PatientModel.organization_id == organization_id,
            PatientModel.patient_number == patient_number.strip(),
            PatientModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return patient_to_domain(model) if model is not None else None

    async def list_by_organization(
        self, organization_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[Patient]:
        stmt = (
            select(PatientModel)
            .where(
                PatientModel.organization_id == organization_id,
                PatientModel.deleted_at.is_(None),
            )
            .order_by(PatientModel.created_at)
            .offset(offset)
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [patient_to_domain(model) for model in models]

    async def add(self, patient: Patient) -> None:
        model = await self._session.get(PatientModel, patient.id)
        if model is None:
            model = PatientModel()
            self._session.add(model)
        apply_patient_to_model(patient, model)
