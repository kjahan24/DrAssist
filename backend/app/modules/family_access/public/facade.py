"""`FamilyAccessFacade` — the one concrete implementation of
`FamilyAccessQueryPort`. Constructed per-request by
`app.modules.family_access.container.build_family_access_facade`, bound
to that request's `AsyncSession`.
"""

from uuid import UUID

from app.modules.family_access.application.services.family_access_query_service import (
    FamilyAccessQueryService,
)
from app.modules.family_access.domain.enums import AccessLevel
from app.modules.family_access.public.dto import FamilyAccessSummaryDTO
from app.modules.family_access.public.interfaces import FamilyAccessQueryPort


class FamilyAccessFacade(FamilyAccessQueryPort):
    def __init__(self, *, query_service: FamilyAccessQueryService) -> None:
        self._query_service = query_service

    async def family_access_exists(self, family_access_id: UUID) -> bool:
        return await self._query_service.family_access_exists(family_access_id)

    async def get_family_access_summary(
        self, family_access_id: UUID
    ) -> FamilyAccessSummaryDTO | None:
        return await self._query_service.get_family_access_summary(family_access_id)

    async def get_patient_caregivers(self, patient_id: UUID) -> list[FamilyAccessSummaryDTO]:
        return await self._query_service.get_patient_caregivers(patient_id)

    async def get_caregiver_patients(self, caregiver_user_id: UUID) -> list[FamilyAccessSummaryDTO]:
        return await self._query_service.get_caregiver_patients(caregiver_user_id)

    async def get_active_access_level(
        self, *, patient_id: UUID, caregiver_user_id: UUID
    ) -> AccessLevel | None:
        return await self._query_service.get_active_access_level(
            patient_id=patient_id, caregiver_user_id=caregiver_user_id
        )
