"""`GetReportService`/`ListReportsService` — read-only report queries.
Combined in one file since both are thin repository wrappers with no
state-mutating logic, mirroring `app.modules.community_engagement
.application.services.vote_query_service`'s identical
`GetVoteStatusService`+`GetVoteCountsService` pairing."""

from uuid import UUID

from app.modules.community_moderation.application.dto import (
    ListReportsInput,
    ReportFeedOutput,
    ReportSummaryDTO,
)
from app.modules.community_moderation.application.services._summary_mappers import (
    report_to_summary,
)
from app.modules.community_moderation.domain.exceptions import ReportNotFoundError
from app.modules.community_moderation.domain.repositories import CommunityReportRepository


class GetReportService:
    def __init__(self, *, report_repository: CommunityReportRepository) -> None:
        self._reports = report_repository

    async def get_report(self, report_id: UUID) -> ReportSummaryDTO:
        report = await self._reports.get_by_id(report_id)
        if report is None:
            raise ReportNotFoundError(report_id)
        return report_to_summary(report)


class ListReportsService:
    def __init__(self, *, report_repository: CommunityReportRepository) -> None:
        self._reports = report_repository

    async def list_reports(self, input_dto: ListReportsInput) -> ReportFeedOutput:
        reports, next_cursor = await self._reports.list_reports(
            organization_id=input_dto.organization_id,
            community_id=input_dto.community_id,
            status=input_dto.status,
            priority=input_dto.priority,
            assigned_moderator_id=input_dto.assigned_moderator_id,
            cursor=input_dto.cursor,
            limit=input_dto.limit,
        )
        return ReportFeedOutput(
            items=[report_to_summary(r) for r in reports], next_cursor=next_cursor
        )
