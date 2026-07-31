"""Read-only queries against `VisitChiefComplaint`.

Backs the module's public `ChiefComplaintQueryPort` — the one
implementation, per
`docs/backend-architecture/04_repository_and_service_patterns.md`'s
service-interface guidance (a formal interface earns its place at the
`public/` boundary; this internal service doesn't need a second one).

`get_chief_complaint_summary`/`ChiefComplaintSummaryDTO`'s extra fields
were added by the REST APIs task — see
`app.modules.diagnosis.application.services.diagnosis_query_service`'s
own docstring for the identical reasoning.
"""

from uuid import UUID

from app.modules.chief_complaints.application.dto import ChiefComplaintSummaryDTO
from app.modules.chief_complaints.domain.entities import VisitChiefComplaint
from app.modules.chief_complaints.domain.repositories import VisitChiefComplaintRepository


class VisitChiefComplaintQueryService:
    def __init__(self, *, chief_complaint_repository: VisitChiefComplaintRepository) -> None:
        self._chief_complaints = chief_complaint_repository

    async def chief_complaint_exists(self, chief_complaint_id: UUID) -> bool:
        return await self._chief_complaints.get_by_id(chief_complaint_id) is not None

    async def get_chief_complaint_summary(
        self, chief_complaint_id: UUID
    ) -> ChiefComplaintSummaryDTO | None:
        complaint = await self._chief_complaints.get_by_id(chief_complaint_id)
        return _to_summary(complaint) if complaint is not None else None

    async def list_chief_complaints_for_visit(
        self, visit_id: UUID
    ) -> list[ChiefComplaintSummaryDTO]:
        complaints = await self._chief_complaints.list_by_visit(visit_id)
        return [_to_summary(complaint) for complaint in complaints]


def _to_summary(complaint: VisitChiefComplaint) -> ChiefComplaintSummaryDTO:
    return ChiefComplaintSummaryDTO(
        chief_complaint_id=complaint.id,
        organization_id=complaint.organization_id,
        visit_id=complaint.visit_id,
        sequence_number=complaint.sequence_number,
        complaint=complaint.complaint,
        duration_value=complaint.duration_value,
        duration_unit=complaint.duration_unit,
        severity=complaint.severity,
        onset=complaint.onset,
        notes=complaint.notes,
        recorded_by=complaint.recorded_by,
        recorded_at=complaint.recorded_at,
    )
