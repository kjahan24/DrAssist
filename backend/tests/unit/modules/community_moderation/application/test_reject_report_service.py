"""Unit tests for `RejectReportService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityRole
from app.modules.community_moderation.application.dto import RejectReportInput
from app.modules.community_moderation.application.services.reject_report_service import (
    RejectReportService,
)
from app.modules.community_moderation.domain.entities import CommunityReport
from app.modules.community_moderation.domain.enums import (
    ModerationTargetType,
    ReportReason,
    ReportStatus,
)
from app.modules.community_moderation.domain.events import ReportRejected
from app.modules.community_moderation.domain.exceptions import (
    InsufficientModeratorRoleError,
    ReportAlreadyClosedError,
    ReportNotFoundError,
)
from tests.unit.modules.community_moderation.application.fakes import (
    FakeCommunityQueryPort,
    FakeCommunityReportRepository,
    FakeUnitOfWork,
    make_member_summary,
)


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


def _seeded() -> (
    tuple[
        RejectReportService, FakeCommunityReportRepository, FakeCommunityQueryPort, FakeUnitOfWork
    ]
):
    reports = FakeCommunityReportRepository()
    communities = FakeCommunityQueryPort()
    uow = FakeUnitOfWork()
    service = RejectReportService(
        report_repository=reports, community_query_port=communities, unit_of_work=uow
    )
    return service, reports, communities, uow


class TestRejectReport:
    async def test_moves_report_to_rejected(self) -> None:
        service, reports, communities, _ = _seeded()
        community_id, moderator_id = uuid4(), uuid4()
        report = _make_report(community_id=community_id)
        await reports.add(report)
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )

        output = await service.execute(
            RejectReportInput(
                report_id=report.id,
                moderator_id=moderator_id,
                community_id=community_id,
                resolution="No violation found.",
            )
        )
        assert output.status is ReportStatus.REJECTED

    async def test_unknown_report_raises(self) -> None:
        service, _, communities, _ = _seeded()
        community_id, moderator_id = uuid4(), uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )
        with pytest.raises(ReportNotFoundError):
            await service.execute(
                RejectReportInput(
                    report_id=uuid4(),
                    moderator_id=moderator_id,
                    community_id=community_id,
                    resolution="No violation.",
                )
            )

    async def test_member_without_moderator_rank_raises(self) -> None:
        service, reports, communities, _ = _seeded()
        community_id, member_id = uuid4(), uuid4()
        report = _make_report(community_id=community_id)
        await reports.add(report)
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=member_id, role=CommunityRole.MEMBER
            )
        )
        with pytest.raises(InsufficientModeratorRoleError):
            await service.execute(
                RejectReportInput(
                    report_id=report.id,
                    moderator_id=member_id,
                    community_id=community_id,
                    resolution="No violation.",
                )
            )

    async def test_raises_once_already_rejected(self) -> None:
        service, reports, communities, _ = _seeded()
        community_id, moderator_id = uuid4(), uuid4()
        report = _make_report(community_id=community_id)
        report.reject(moderator_id=uuid4(), resolution="First rejection.")
        await reports.add(report)
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )
        with pytest.raises(ReportAlreadyClosedError):
            await service.execute(
                RejectReportInput(
                    report_id=report.id,
                    moderator_id=moderator_id,
                    community_id=community_id,
                    resolution="Second rejection.",
                )
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, reports, communities, uow = _seeded()
        community_id, moderator_id = uuid4(), uuid4()
        report = _make_report(community_id=community_id)
        await reports.add(report)
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )
        await service.execute(
            RejectReportInput(
                report_id=report.id,
                moderator_id=moderator_id,
                community_id=community_id,
                resolution="No violation.",
            )
        )
        assert uow.committed is True

    async def test_publishes_a_report_rejected_event(self) -> None:
        service, reports, communities, uow = _seeded()
        community_id, moderator_id = uuid4(), uuid4()
        report = _make_report(community_id=community_id)
        await reports.add(report)
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )
        await service.execute(
            RejectReportInput(
                report_id=report.id,
                moderator_id=moderator_id,
                community_id=community_id,
                resolution="No violation.",
            )
        )
        assert any(isinstance(e, ReportRejected) for e in uow.published_events)
