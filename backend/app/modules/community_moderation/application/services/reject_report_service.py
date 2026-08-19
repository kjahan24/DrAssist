"""`RejectReportService` — closes an open report as `REJECTED` (no
violation found)."""

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_moderation.application.dto import RejectReportInput, ReportSummaryDTO
from app.modules.community_moderation.application.services._authorization import (
    ensure_is_moderator,
)
from app.modules.community_moderation.application.services._summary_mappers import (
    report_to_summary,
)
from app.modules.community_moderation.domain.exceptions import ReportNotFoundError
from app.modules.community_moderation.domain.repositories import CommunityReportRepository
from app.shared.application.unit_of_work import UnitOfWork


class RejectReportService:
    def __init__(
        self,
        *,
        report_repository: CommunityReportRepository,
        community_query_port: CommunityQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._reports = report_repository
        self._communities = community_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: RejectReportInput) -> ReportSummaryDTO:
        report = await self._reports.get_by_id(input_dto.report_id)
        if report is None:
            raise ReportNotFoundError(input_dto.report_id)

        member = await self._communities.get_membership(
            input_dto.community_id, input_dto.moderator_id
        )
        ensure_is_moderator(
            member, community_id=input_dto.community_id, user_id=input_dto.moderator_id
        )

        report.reject(
            moderator_id=input_dto.moderator_id,
            resolution=input_dto.resolution,
            note=input_dto.note,
        )
        await self._reports.add(report)
        self._uow.collect_events(report.pull_events())
        await self._uow.commit()
        return report_to_summary(report)
