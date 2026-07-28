"""Read-only queries against `VisitVitalSigns`.

Backs the module's public `VitalSignsQueryPort` — the one implementation,
per `docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).
"""

from uuid import UUID

from app.modules.vital_signs.application.dto import VitalSignsSummaryDTO
from app.modules.vital_signs.domain.repositories import VisitVitalSignsRepository


class VisitVitalSignsQueryService:
    def __init__(self, *, vital_signs_repository: VisitVitalSignsRepository) -> None:
        self._vital_signs = vital_signs_repository

    async def vital_signs_exist_for_visit(self, visit_id: UUID) -> bool:
        return await self._vital_signs.get_by_visit_id(visit_id) is not None

    async def get_vital_signs_summary_for_visit(
        self, visit_id: UUID
    ) -> VitalSignsSummaryDTO | None:
        vital_signs = await self._vital_signs.get_by_visit_id(visit_id)
        if vital_signs is None:
            return None
        return VitalSignsSummaryDTO(
            vital_signs_id=vital_signs.id,
            organization_id=vital_signs.organization_id,
            visit_id=vital_signs.visit_id,
            recorded_at=vital_signs.recorded_at,
            bmi=vital_signs.bmi,
        )
