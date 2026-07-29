"""Concrete SQLAlchemy repository implementation.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — see the identical pattern (and rationale) in
`app.modules.clinical_reasoning.infrastructure.repositories`.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.differential_diagnosis.domain.entities import DifferentialDiagnosis
from app.modules.differential_diagnosis.domain.repositories import (
    DifferentialDiagnosisRepository,
)
from app.modules.differential_diagnosis.infrastructure.mappers import (
    apply_differential_diagnosis_to_model,
    differential_diagnosis_to_domain,
)
from app.modules.differential_diagnosis.infrastructure.models import DifferentialDiagnosisModel


class SqlAlchemyDifferentialDiagnosisRepository(DifferentialDiagnosisRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, differential_diagnosis_id: UUID) -> DifferentialDiagnosis | None:
        model = await self._session.get(DifferentialDiagnosisModel, differential_diagnosis_id)
        if model is None or model.deleted_at is not None:
            return None
        return differential_diagnosis_to_domain(model)

    async def get_by_clinical_note_and_ranking(
        self, *, clinical_note_id: UUID, ranking: int
    ) -> DifferentialDiagnosis | None:
        stmt = select(DifferentialDiagnosisModel).where(
            DifferentialDiagnosisModel.clinical_note_id == clinical_note_id,
            DifferentialDiagnosisModel.ranking == ranking,
            DifferentialDiagnosisModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return differential_diagnosis_to_domain(model) if model is not None else None

    async def list_by_clinical_note(self, clinical_note_id: UUID) -> list[DifferentialDiagnosis]:
        stmt = (
            select(DifferentialDiagnosisModel)
            .where(
                DifferentialDiagnosisModel.clinical_note_id == clinical_note_id,
                DifferentialDiagnosisModel.deleted_at.is_(None),
            )
            .order_by(DifferentialDiagnosisModel.ranking)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [differential_diagnosis_to_domain(model) for model in models]

    async def list_by_patient(self, patient_id: UUID) -> list[DifferentialDiagnosis]:
        stmt = (
            select(DifferentialDiagnosisModel)
            .where(
                DifferentialDiagnosisModel.patient_id == patient_id,
                DifferentialDiagnosisModel.deleted_at.is_(None),
            )
            .order_by(DifferentialDiagnosisModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [differential_diagnosis_to_domain(model) for model in models]

    async def add(self, diagnosis: DifferentialDiagnosis) -> None:
        model = await self._session.get(DifferentialDiagnosisModel, diagnosis.id)
        if model is None:
            model = DifferentialDiagnosisModel()
            self._session.add(model)
        apply_differential_diagnosis_to_model(diagnosis, model)
