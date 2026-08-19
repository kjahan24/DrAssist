"""Unit tests for `GetReportService`/`ListReportsService`."""

from uuid import uuid4

import pytest

from app.modules.community_moderation.application.dto import ListReportsInput
from app.modules.community_moderation.application.services.report_query_service import (
    GetReportService,
    ListReportsService,
)
from app.modules.community_moderation.domain.entities import CommunityReport
from app.modules.community_moderation.domain.enums import (
    ModerationTargetType,
    ReportPriority,
    ReportReason,
    ReportStatus,
)
from app.modules.community_moderation.domain.exceptions import ReportNotFoundError
from tests.unit.modules.community_moderation.application.fakes import FakeCommunityReportRepository


def _make_report(**overrides: object) -> CommunityReport:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "community_id": uuid4(),
        "reporter_id": uuid4(),
        "target_type": ModerationTargetType.POST,
        "target_id": uuid4(),
        "reason": ReportReason.SPAM,
    }
    defaults.update(overrides)
    return CommunityReport.create(**defaults)  # type: ignore[arg-type]


class TestGetReport:
    async def test_returns_the_matching_report(self) -> None:
        reports = FakeCommunityReportRepository()
        service = GetReportService(report_repository=reports)
        report = _make_report()
        await reports.add(report)

        result = await service.get_report(report.id)
        assert result.report_id == report.id

    async def test_unknown_report_raises(self) -> None:
        reports = FakeCommunityReportRepository()
        service = GetReportService(report_repository=reports)
        with pytest.raises(ReportNotFoundError):
            await service.get_report(uuid4())


class TestListReports:
    async def test_scopes_to_the_organization(self) -> None:
        reports = FakeCommunityReportRepository()
        service = ListReportsService(report_repository=reports)
        org_id = uuid4()
        mine = _make_report(organization_id=org_id)
        theirs = _make_report(organization_id=uuid4())
        await reports.add(mine)
        await reports.add(theirs)

        result = await service.list_reports(ListReportsInput(organization_id=org_id))
        assert [r.report_id for r in result.items] == [mine.id]

    async def test_filters_by_community(self) -> None:
        reports = FakeCommunityReportRepository()
        service = ListReportsService(report_repository=reports)
        org_id, community_id = uuid4(), uuid4()
        mine = _make_report(organization_id=org_id, community_id=community_id)
        other = _make_report(organization_id=org_id, community_id=uuid4())
        await reports.add(mine)
        await reports.add(other)

        result = await service.list_reports(
            ListReportsInput(organization_id=org_id, community_id=community_id)
        )
        assert [r.report_id for r in result.items] == [mine.id]

    async def test_filters_by_status(self) -> None:
        reports = FakeCommunityReportRepository()
        service = ListReportsService(report_repository=reports)
        org_id = uuid4()
        open_report = _make_report(organization_id=org_id)
        resolved_report = _make_report(organization_id=org_id)
        resolved_report.resolve(moderator_id=uuid4(), resolution="Done.")
        await reports.add(open_report)
        await reports.add(resolved_report)

        result = await service.list_reports(
            ListReportsInput(organization_id=org_id, status=ReportStatus.RESOLVED)
        )
        assert [r.report_id for r in result.items] == [resolved_report.id]

    async def test_filters_by_priority(self) -> None:
        reports = FakeCommunityReportRepository()
        service = ListReportsService(report_repository=reports)
        org_id = uuid4()
        high = _make_report(organization_id=org_id, reason=ReportReason.SELF_HARM_CONCERN)
        low = _make_report(organization_id=org_id, reason=ReportReason.SPAM)
        await reports.add(high)
        await reports.add(low)

        result = await service.list_reports(
            ListReportsInput(organization_id=org_id, priority=ReportPriority.HIGH)
        )
        assert [r.report_id for r in result.items] == [high.id]

    async def test_filters_by_assigned_moderator(self) -> None:
        reports = FakeCommunityReportRepository()
        service = ListReportsService(report_repository=reports)
        org_id, moderator_id = uuid4(), uuid4()
        assigned = _make_report(organization_id=org_id)
        assigned.assign(moderator_id=moderator_id)
        unassigned = _make_report(organization_id=org_id)
        await reports.add(assigned)
        await reports.add(unassigned)

        result = await service.list_reports(
            ListReportsInput(organization_id=org_id, assigned_moderator_id=moderator_id)
        )
        assert [r.report_id for r in result.items] == [assigned.id]

    async def test_returns_empty_feed_when_no_reports_exist(self) -> None:
        reports = FakeCommunityReportRepository()
        service = ListReportsService(report_repository=reports)
        result = await service.list_reports(ListReportsInput(organization_id=uuid4()))
        assert result.items == []
        assert result.next_cursor is None
