"""Concrete SQLAlchemy repository implementation.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — see the identical pattern (and rationale) in
`app.modules.documents.infrastructure.repositories`.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.family_access.domain.entities import FamilyAccess
from app.modules.family_access.domain.enums import FamilyAccessStatus
from app.modules.family_access.domain.repositories import FamilyAccessRepository
from app.modules.family_access.domain.value_objects import InvitationTokenHash
from app.modules.family_access.infrastructure.mappers import (
    apply_family_access_to_model,
    family_access_to_domain,
)
from app.modules.family_access.infrastructure.models import FamilyAccessModel

_ACTIVE_STATUSES = (FamilyAccessStatus.PENDING, FamilyAccessStatus.ACCEPTED)


class SqlAlchemyFamilyAccessRepository(FamilyAccessRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, family_access_id: UUID) -> FamilyAccess | None:
        model = await self._session.get(FamilyAccessModel, family_access_id)
        if model is None or model.deleted_at is not None:
            return None
        return family_access_to_domain(model)

    async def get_by_invitation_token(
        self, invitation_token: InvitationTokenHash
    ) -> FamilyAccess | None:
        stmt = select(FamilyAccessModel).where(
            FamilyAccessModel.invitation_token == str(invitation_token),
            FamilyAccessModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return family_access_to_domain(model) if model is not None else None

    async def get_active_by_patient_and_caregiver(
        self, *, patient_id: UUID, caregiver_user_id: UUID
    ) -> FamilyAccess | None:
        stmt = select(FamilyAccessModel).where(
            FamilyAccessModel.patient_id == patient_id,
            FamilyAccessModel.caregiver_user_id == caregiver_user_id,
            FamilyAccessModel.status.in_(_ACTIVE_STATUSES),
            FamilyAccessModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return family_access_to_domain(model) if model is not None else None

    async def list_by_patient(self, patient_id: UUID) -> list[FamilyAccess]:
        stmt = (
            select(FamilyAccessModel)
            .where(
                FamilyAccessModel.patient_id == patient_id,
                FamilyAccessModel.deleted_at.is_(None),
            )
            .order_by(FamilyAccessModel.created_at.desc())
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [family_access_to_domain(model) for model in models]

    async def list_by_caregiver(self, caregiver_user_id: UUID) -> list[FamilyAccess]:
        stmt = (
            select(FamilyAccessModel)
            .where(
                FamilyAccessModel.caregiver_user_id == caregiver_user_id,
                FamilyAccessModel.deleted_at.is_(None),
            )
            .order_by(FamilyAccessModel.created_at.desc())
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [family_access_to_domain(model) for model in models]

    async def list_pending_by_caregiver(self, caregiver_user_id: UUID) -> list[FamilyAccess]:
        stmt = (
            select(FamilyAccessModel)
            .where(
                FamilyAccessModel.caregiver_user_id == caregiver_user_id,
                FamilyAccessModel.status == FamilyAccessStatus.PENDING,
                FamilyAccessModel.deleted_at.is_(None),
            )
            .order_by(FamilyAccessModel.created_at.desc())
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [family_access_to_domain(model) for model in models]

    async def add(self, family_access: FamilyAccess) -> None:
        model = await self._session.get(FamilyAccessModel, family_access.id)
        if model is None:
            model = FamilyAccessModel()
            self._session.add(model)
        apply_family_access_to_model(family_access, model)
