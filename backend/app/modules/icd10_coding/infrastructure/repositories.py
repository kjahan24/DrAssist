"""Concrete SQLAlchemy repository implementation.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — see the identical pattern (and rationale) in
`app.modules.differential_diagnosis.infrastructure.repositories`.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.icd10_coding.domain.entities import ICD10Coding
from app.modules.icd10_coding.domain.repositories import ICD10CodingRepository
from app.modules.icd10_coding.infrastructure.mappers import (
    apply_icd10_coding_to_model,
    icd10_coding_to_domain,
)
from app.modules.icd10_coding.infrastructure.models import ICD10CodingModel


class SqlAlchemyICD10CodingRepository(ICD10CodingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, icd10_coding_id: UUID) -> ICD10Coding | None:
        model = await self._session.get(ICD10CodingModel, icd10_coding_id)
        if model is None or model.deleted_at is not None:
            return None
        return icd10_coding_to_domain(model)

    async def get_primary_for_clinical_note(self, clinical_note_id: UUID) -> ICD10Coding | None:
        stmt = select(ICD10CodingModel).where(
            ICD10CodingModel.clinical_note_id == clinical_note_id,
            ICD10CodingModel.primary_code.is_(True),
            ICD10CodingModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return icd10_coding_to_domain(model) if model is not None else None

    async def list_by_clinical_note(self, clinical_note_id: UUID) -> list[ICD10Coding]:
        stmt = (
            select(ICD10CodingModel)
            .where(
                ICD10CodingModel.clinical_note_id == clinical_note_id,
                ICD10CodingModel.deleted_at.is_(None),
            )
            .order_by(ICD10CodingModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [icd10_coding_to_domain(model) for model in models]

    async def list_by_patient(self, patient_id: UUID) -> list[ICD10Coding]:
        stmt = (
            select(ICD10CodingModel)
            .where(
                ICD10CodingModel.patient_id == patient_id,
                ICD10CodingModel.deleted_at.is_(None),
            )
            .order_by(ICD10CodingModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [icd10_coding_to_domain(model) for model in models]

    async def add(self, coding: ICD10Coding) -> None:
        model = await self._session.get(ICD10CodingModel, coding.id)
        if model is None:
            model = ICD10CodingModel()
            self._session.add(model)
        apply_icd10_coding_to_model(coding, model)
