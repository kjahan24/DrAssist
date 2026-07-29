"""Concrete SQLAlchemy repository implementations.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — see the identical pattern (and rationale) in
`app.modules.soap_notes.infrastructure.repositories`.

Neither repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.prescriptions.domain.entities import Prescription, PrescriptionItem
from app.modules.prescriptions.domain.repositories import (
    PrescriptionItemRepository,
    PrescriptionRepository,
)
from app.modules.prescriptions.infrastructure.mappers import (
    apply_prescription_item_to_model,
    apply_prescription_to_model,
    prescription_item_to_domain,
    prescription_to_domain,
)
from app.modules.prescriptions.infrastructure.models import PrescriptionItemModel, PrescriptionModel


class SqlAlchemyPrescriptionRepository(PrescriptionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, prescription_id: UUID) -> Prescription | None:
        model = await self._session.get(PrescriptionModel, prescription_id)
        if model is None or model.deleted_at is not None:
            return None
        return prescription_to_domain(model)

    async def get_by_clinical_note_id(self, clinical_note_id: UUID) -> Prescription | None:
        stmt = select(PrescriptionModel).where(
            PrescriptionModel.clinical_note_id == clinical_note_id,
            PrescriptionModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return prescription_to_domain(model) if model is not None else None

    async def get_by_prescription_number(self, prescription_number: str) -> Prescription | None:
        stmt = select(PrescriptionModel).where(
            PrescriptionModel.prescription_number == prescription_number.strip(),
            PrescriptionModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return prescription_to_domain(model) if model is not None else None

    async def list_by_patient(self, patient_id: UUID) -> list[Prescription]:
        stmt = (
            select(PrescriptionModel)
            .where(
                PrescriptionModel.patient_id == patient_id,
                PrescriptionModel.deleted_at.is_(None),
            )
            .order_by(PrescriptionModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [prescription_to_domain(model) for model in models]

    async def add(self, prescription: Prescription) -> None:
        model = await self._session.get(PrescriptionModel, prescription.id)
        if model is None:
            model = PrescriptionModel()
            self._session.add(model)
        apply_prescription_to_model(prescription, model)


class SqlAlchemyPrescriptionItemRepository(PrescriptionItemRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, prescription_item_id: UUID) -> PrescriptionItem | None:
        model = await self._session.get(PrescriptionItemModel, prescription_item_id)
        return prescription_item_to_domain(model) if model is not None else None

    async def list_by_prescription(self, prescription_id: UUID) -> list[PrescriptionItem]:
        stmt = (
            select(PrescriptionItemModel)
            .where(PrescriptionItemModel.prescription_id == prescription_id)
            .order_by(PrescriptionItemModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [prescription_item_to_domain(model) for model in models]

    async def add(self, item: PrescriptionItem) -> None:
        model = await self._session.get(PrescriptionItemModel, item.id)
        if model is None:
            model = PrescriptionItemModel()
            self._session.add(model)
        apply_prescription_item_to_model(item, model)
