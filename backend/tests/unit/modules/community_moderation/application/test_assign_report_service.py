"""Unit tests for `AssignReportService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityRole
from app.modules.community_moderation.application.dto import AssignReportInput
from app.modules.community_moderation.application.services.assign_report_service import (
    AssignReportService,
)
from app.modules.community_moderation.domain.entities import CommunityReport
from app.modules.community_moderation.domain.enums import (
    ModerationTargetType,
    ReportReason,
    ReportStatus,
)
from app.modules.community_moderation.domain.events import ReportAssigned
from app.modules.community_moderation.domain.exceptions import (
    InsufficientModeratorRoleError,
    ModerationMembershipRequiredError,
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
        AssignReportService, FakeCommunityReportRepository, FakeCommunityQueryPort, FakeUnitOfWork
    ]
):
    reports = FakeCommunityReportRepository()
    communities = FakeCommunityQueryPort()
    uow = FakeUnitOfWork()
    service = AssignReportService(
        report_repository=reports, community_query_port=communities, unit_of_work=uow
    )
    return service, reports, communities, uow


class TestAssignReport:
    async def test_moves_report_to_under_review(self) -> None:
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
            AssignReportInput(
                report_id=report.id, moderator_id=moderator_id, community_id=community_id
            )
        )
        assert output.status is ReportStatus.UNDER_REVIEW
        assert output.assigned_moderator_id == moderator_id

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
                AssignReportInput(
                    report_id=uuid4(), moderator_id=moderator_id, community_id=community_id
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
                AssignReportInput(
                    report_id=report.id, moderator_id=member_id, community_id=community_id
                )
            )

    async def test_non_member_raises(self) -> None:
        service, reports, _, _ = _seeded()
        community_id = uuid4()
        report = _make_report(community_id=community_id)
        await reports.add(report)
        with pytest.raises(ModerationMembershipRequiredError):
            await service.execute(
                AssignReportInput(
                    report_id=report.id, moderator_id=uuid4(), community_id=community_id
                )
            )

    async def test_reassign_while_under_review_is_allowed(self) -> None:
        service, reports, communities, _ = _seeded()
        community_id, first_mod, second_mod = uuid4(), uuid4(), uuid4()
        report = _make_report(community_id=community_id)
        await reports.add(report)
        for mod_id in (first_mod, second_mod):
            communities.add_membership(
                make_member_summary(
                    community_id=community_id, user_id=mod_id, role=CommunityRole.MODERATOR
                )
            )
        await service.execute(
            AssignReportInput(
                report_id=report.id, moderator_id=first_mod, community_id=community_id
            )
        )
        output = await service.execute(
            AssignReportInput(
                report_id=report.id, moderator_id=second_mod, community_id=community_id
            )
        )
        assert output.assigned_moderator_id == second_mod

    async def test_raises_once_resolved(self) -> None:
        service, reports, communities, _ = _seeded()
        community_id, moderator_id = uuid4(), uuid4()
        report = _make_report(community_id=community_id)
        report.resolve(moderator_id=uuid4(), resolution="Done.")
        await reports.add(report)
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )
        with pytest.raises(ReportAlreadyClosedError):
            await service.execute(
                AssignReportInput(
                    report_id=report.id, moderator_id=moderator_id, community_id=community_id
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
            AssignReportInput(
                report_id=report.id, moderator_id=moderator_id, community_id=community_id
            )
        )
        assert uow.committed is True

    async def test_publishes_a_report_assigned_event(self) -> None:
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
            AssignReportInput(
                report_id=report.id, moderator_id=moderator_id, community_id=community_id
            )
        )
        assert any(isinstance(e, ReportAssigned) for e in uow.published_events)
