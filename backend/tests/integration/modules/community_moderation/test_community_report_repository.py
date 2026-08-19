"""Integration tests for `SqlAlchemyCommunityReportRepository` against a
real PostgreSQL instance: round-trip persistence, `get_open_report`,
`list_reports` filtering/cursor pagination, and the partial unique index
backing "Prevent duplicate reports"."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.community_moderation._helpers import persist_org_user_community

from app.modules.community_moderation.domain.entities import CommunityReport
from app.modules.community_moderation.domain.enums import (
    ModerationTargetType,
    ReportPriority,
    ReportReason,
    ReportStatus,
)
from app.modules.community_moderation.infrastructure.repositories import (
    SqlAlchemyCommunityReportRepository,
)


class TestCommunityReportRoundTrip:
    async def test_save_and_reload(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        repo = SqlAlchemyCommunityReportRepository(db_session)
        target_id = uuid4()
        report = CommunityReport.create(
            organization_id=organization.id,
            community_id=community.id,
            reporter_id=user.id,
            target_type=ModerationTargetType.POST,
            target_id=target_id,
            reason=ReportReason.SPAM,
            description="Repeated spam links.",
        )

        await repo.add(report)
        await db_session.commit()

        reloaded = await repo.get_by_id(report.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.community_id == community.id
        assert reloaded.reporter_id == user.id
        assert reloaded.target_id == target_id
        assert reloaded.reason is ReportReason.SPAM
        assert reloaded.status is ReportStatus.OPEN
        assert reloaded.priority is ReportPriority.LOW
        assert reloaded.description == "Repeated spam links."

    async def test_round_trip_preserves_assignment_and_resolution(
        self, db_session: AsyncSession
    ) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        _, moderator = organization, user
        repo = SqlAlchemyCommunityReportRepository(db_session)
        report = CommunityReport.create(
            organization_id=organization.id,
            community_id=community.id,
            reporter_id=user.id,
            target_type=ModerationTargetType.POST,
            target_id=uuid4(),
            reason=ReportReason.HARASSMENT,
        )
        report.resolve(moderator_id=moderator.id, resolution="Content removed.", note="Escalated.")
        await repo.add(report)
        await db_session.commit()

        reloaded = await repo.get_by_id(report.id)
        assert reloaded is not None
        assert reloaded.status is ReportStatus.RESOLVED
        assert reloaded.assigned_moderator_id == moderator.id
        assert reloaded.resolution == "Content removed."
        assert reloaded.moderator_note == "Escalated."
        assert reloaded.resolved_at is not None


class TestGetOpenReport:
    async def test_returns_none_when_absent(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityReportRepository(db_session)
        result = await repo.get_open_report(uuid4(), ModerationTargetType.POST, uuid4())
        assert result is None

    async def test_returns_the_open_report(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        repo = SqlAlchemyCommunityReportRepository(db_session)
        target_id = uuid4()
        report = CommunityReport.create(
            organization_id=organization.id,
            community_id=community.id,
            reporter_id=user.id,
            target_type=ModerationTargetType.POST,
            target_id=target_id,
            reason=ReportReason.SPAM,
        )
        await repo.add(report)
        await db_session.commit()

        found = await repo.get_open_report(user.id, ModerationTargetType.POST, target_id)
        assert found is not None
        assert found.id == report.id

    async def test_ignores_a_resolved_report(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        repo = SqlAlchemyCommunityReportRepository(db_session)
        target_id = uuid4()
        report = CommunityReport.create(
            organization_id=organization.id,
            community_id=community.id,
            reporter_id=user.id,
            target_type=ModerationTargetType.POST,
            target_id=target_id,
            reason=ReportReason.SPAM,
        )
        report.resolve(moderator_id=user.id, resolution="Done.")
        await repo.add(report)
        await db_session.commit()

        found = await repo.get_open_report(user.id, ModerationTargetType.POST, target_id)
        assert found is None


class TestListReports:
    async def test_scopes_to_the_organization(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        repo = SqlAlchemyCommunityReportRepository(db_session)
        mine = CommunityReport.create(
            organization_id=organization.id,
            community_id=community.id,
            reporter_id=user.id,
            target_type=ModerationTargetType.POST,
            target_id=uuid4(),
            reason=ReportReason.SPAM,
        )
        await repo.add(mine)
        await db_session.commit()

        results, _ = await repo.list_reports(organization_id=organization.id)
        assert mine.id in [r.id for r in results]

    async def test_filters_by_status(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        repo = SqlAlchemyCommunityReportRepository(db_session)
        resolved = CommunityReport.create(
            organization_id=organization.id,
            community_id=community.id,
            reporter_id=user.id,
            target_type=ModerationTargetType.POST,
            target_id=uuid4(),
            reason=ReportReason.SPAM,
        )
        resolved.resolve(moderator_id=user.id, resolution="Done.")
        await repo.add(resolved)
        await db_session.commit()

        results, _ = await repo.list_reports(
            organization_id=organization.id, status=ReportStatus.RESOLVED
        )
        assert resolved.id in [r.id for r in results]

    async def test_respects_cursor_pagination(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        repo = SqlAlchemyCommunityReportRepository(db_session)
        created = []
        for _ in range(3):
            report = CommunityReport.create(
                organization_id=organization.id,
                community_id=community.id,
                reporter_id=user.id,
                target_type=ModerationTargetType.POST,
                target_id=uuid4(),
                reason=ReportReason.SPAM,
            )
            await repo.add(report)
            await db_session.commit()
            created.append(report.id)

        first_page, next_cursor = await repo.list_reports(
            organization_id=organization.id, community_id=community.id, limit=2
        )
        assert len(first_page) == 2
        assert next_cursor is not None

        second_page, second_cursor = await repo.list_reports(
            organization_id=organization.id,
            community_id=community.id,
            cursor=next_cursor,
            limit=2,
        )
        assert len(second_page) == 1
        assert second_cursor is None


class TestDuplicateOpenReportConstraint:
    async def test_duplicate_open_report_row_violates_the_partial_unique_index(
        self, db_session: AsyncSession
    ) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        repo = SqlAlchemyCommunityReportRepository(db_session)
        target_id = uuid4()

        first = CommunityReport.create(
            organization_id=organization.id,
            community_id=community.id,
            reporter_id=user.id,
            target_type=ModerationTargetType.POST,
            target_id=target_id,
            reason=ReportReason.SPAM,
        )
        await repo.add(first)
        await db_session.commit()

        second = CommunityReport.create(
            organization_id=organization.id,
            community_id=community.id,
            reporter_id=user.id,
            target_type=ModerationTargetType.POST,
            target_id=target_id,
            reason=ReportReason.HARASSMENT,
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    async def test_a_new_report_after_resolution_does_not_violate_the_index(
        self, db_session: AsyncSession
    ) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        repo = SqlAlchemyCommunityReportRepository(db_session)
        target_id = uuid4()

        first = CommunityReport.create(
            organization_id=organization.id,
            community_id=community.id,
            reporter_id=user.id,
            target_type=ModerationTargetType.POST,
            target_id=target_id,
            reason=ReportReason.SPAM,
        )
        first.resolve(moderator_id=user.id, resolution="Done.")
        await repo.add(first)
        await db_session.commit()

        second = CommunityReport.create(
            organization_id=organization.id,
            community_id=community.id,
            reporter_id=user.id,
            target_type=ModerationTargetType.POST,
            target_id=target_id,
            reason=ReportReason.HARASSMENT,
        )
        await repo.add(second)
        await db_session.commit()  # must not raise

        reloaded = await repo.get_by_id(second.id)
        assert reloaded is not None


class TestCommunityReportRequiresValidReferences:
    async def test_nonexistent_reporter_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _, community = await persist_org_user_community(db_session)
        repo = SqlAlchemyCommunityReportRepository(db_session)
        report = CommunityReport.create(
            organization_id=organization.id,
            community_id=community.id,
            reporter_id=uuid4(),
            target_type=ModerationTargetType.POST,
            target_id=uuid4(),
            reason=ReportReason.SPAM,
        )
        await repo.add(report)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
