"""Read-only queries against `VisitChiefComplaint`.

Backs the module's public `ChiefComplaintQueryPort` — the one
implementation, per
`docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).
"""

from uuid import UUID

from app.modules.chief_complaints.application.dto import ChiefComplaintSummaryDTO
from app.modules.chief_complaints.domain.repositories import VisitChiefComplaintRepository


class VisitChiefComplaintQueryService:
    def __init__(self, *, chief_complaint_repository: VisitChiefComplaintRepository) -> None:
        self._chief_complaints = chief_complaint_repository

    async def chief_complaint_exists(self, chief_complaint_id: UUID) -> bool:
        return await self._chief_complaints.get_by_id(chief_complaint_id) is not None

    async def list_chief_complaints_for_visit(
        self, visit_id: UUID
    ) -> list[ChiefComplaintSummaryDTO]:
        complaints = await self._chief_complaints.list_by_visit(visit_id)
        return [
            ChiefComplaintSummaryDTO(
                chief_complaint_id=complaint.id,
                organization_id=complaint.organization_id,
                visit_id=complaint.visit_id,
                sequence_number=complaint.sequence_number,
                complaint=complaint.complaint,
            )
            for complaint in complaints
        ]
