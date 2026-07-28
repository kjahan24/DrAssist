"""Read-only queries against `PatientVisit`.

Backs the module's public `VisitQueryPort` — the one implementation, per
`docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).
"""

from uuid import UUID

from app.modules.visit.application.dto import VisitSummaryDTO
from app.modules.visit.domain.enums import VisitStatus
from app.modules.visit.domain.repositories import PatientVisitRepository

_NON_TERMINAL_STATUSES = frozenset(
    {VisitStatus.SCHEDULED, VisitStatus.CHECKED_IN, VisitStatus.IN_PROGRESS}
)


class PatientVisitQueryService:
    def __init__(self, *, patient_visit_repository: PatientVisitRepository) -> None:
        self._visits = patient_visit_repository

    async def visit_exists(self, visit_id: UUID) -> bool:
        return await self._visits.get_by_id(visit_id) is not None

    async def is_active(self, visit_id: UUID) -> bool:
        """ "Active" means not yet in a terminal state (`Completed`,
        `Cancelled`, `No Show`) — i.e. still scheduled, checked in, or in
        progress."""
        visit = await self._visits.get_by_id(visit_id)
        return visit is not None and visit.visit_status in _NON_TERMINAL_STATUSES

    async def get_visit_summary(self, visit_id: UUID) -> VisitSummaryDTO | None:
        visit = await self._visits.get_by_id(visit_id)
        if visit is None:
            return None
        return VisitSummaryDTO(
            visit_id=visit.id,
            organization_id=visit.organization_id,
            patient_id=visit.patient_id,
            doctor_id=visit.doctor_id,
            visit_number=visit.visit_number,
            visit_status=visit.visit_status,
        )
