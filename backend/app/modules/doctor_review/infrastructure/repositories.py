"""Concrete SQLAlchemy repository implementation.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — see the identical pattern (and rationale) in
`app.modules.icd10_coding.infrastructure.repositories`.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.doctor_review.domain.entities import DoctorReview
from app.modules.doctor_review.domain.repositories import DoctorReviewRepository
from app.modules.doctor_review.infrastructure.mappers import (
    apply_doctor_review_to_model,
    doctor_review_to_domain,
)
from app.modules.doctor_review.infrastructure.models import DoctorReviewModel


class SqlAlchemyDoctorReviewRepository(DoctorReviewRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, doctor_review_id: UUID) -> DoctorReview | None:
        model = await self._session.get(DoctorReviewModel, doctor_review_id)
        if model is None or model.deleted_at is not None:
            return None
        return doctor_review_to_domain(model)

    async def get_by_clinical_note_id(self, clinical_note_id: UUID) -> DoctorReview | None:
        stmt = select(DoctorReviewModel).where(
            DoctorReviewModel.clinical_note_id == clinical_note_id,
            DoctorReviewModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return doctor_review_to_domain(model) if model is not None else None

    async def list_by_patient(self, patient_id: UUID) -> list[DoctorReview]:
        stmt = (
            select(DoctorReviewModel)
            .where(
                DoctorReviewModel.patient_id == patient_id,
                DoctorReviewModel.deleted_at.is_(None),
            )
            .order_by(DoctorReviewModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [doctor_review_to_domain(model) for model in models]

    async def add(self, review: DoctorReview) -> None:
        model = await self._session.get(DoctorReviewModel, review.id)
        if model is None:
            model = DoctorReviewModel()
            self._session.add(model)
        apply_doctor_review_to_model(review, model)
