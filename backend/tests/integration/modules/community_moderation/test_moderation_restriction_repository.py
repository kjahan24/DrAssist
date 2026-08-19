"""Integration tests for `SqlAlchemyModerationRestrictionRepository`
against a real PostgreSQL instance: round-trip persistence,
`list_active_for_user` (time-window filtering), `list_for_user` cursor
pagination."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.community_moderation._helpers import (
    persist_community,
    persist_org_user,
    persist_org_user_community,
)

from app.modules.community_moderation.domain.entities import ModerationRestriction
from app.modules.community_moderation.domain.enums import ModerationRestrictionType
from app.modules.community_moderation.infrastructure.repositories import (
    SqlAlchemyModerationRestrictionRepository,
)


class TestModerationRestrictionRoundTrip:
    async def test_save_and_reload(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        repo = SqlAlchemyModerationRestrictionRepository(db_session)
        restriction = ModerationRestriction.issue(
            organization_id=organization.id,
            community_id=community.id,
            user_id=user.id,
            issued_by=user.id,
            restriction_type=ModerationRestrictionType.WARNING,
            reason="Repeated spam links.",
        )

        await repo.add(restriction)
        await db_session.commit()

        reloaded = await repo.get_by_id(restriction.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.community_id == community.id
        assert reloaded.user_id == user.id
        assert reloaded.restriction_type is ModerationRestrictionType.WARNING
        assert reloaded.reason == "Repeated spam links."
        assert reloaded.ends_at is None
        # `updated_at` is synthesized from `created_at` on load — see
        # `infrastructure/mappers.py`'s own docstring.
        assert reloaded.updated_at == reloaded.created_at

    async def test_round_trip_preserves_ends_at(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        repo = SqlAlchemyModerationRestrictionRepository(db_session)
        ends_at = datetime.now(UTC) + timedelta(days=7)
        restriction = ModerationRestriction.issue(
            organization_id=organization.id,
            community_id=community.id,
            user_id=user.id,
            issued_by=user.id,
            restriction_type=ModerationRestrictionType.SUSPENSION,
            reason="Repeated abuse.",
            ends_at=ends_at,
        )
        await repo.add(restriction)
        await db_session.commit()

        reloaded = await repo.get_by_id(restriction.id)
        assert reloaded is not None
        assert reloaded.ends_at is not None


class TestListActiveForUser:
    async def test_active_restriction_is_returned(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        repo = SqlAlchemyModerationRestrictionRepository(db_session)
        restriction = ModerationRestriction.issue(
            organization_id=organization.id,
            community_id=community.id,
            user_id=user.id,
            issued_by=user.id,
            restriction_type=ModerationRestrictionType.WARNING,
            reason="Reason.",
        )
        await repo.add(restriction)
        await db_session.commit()

        active = await repo.list_active_for_user(user.id)
        assert [r.id for r in active] == [restriction.id]

    async def test_expired_restriction_is_excluded(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        repo = SqlAlchemyModerationRestrictionRepository(db_session)
        restriction = ModerationRestriction.issue(
            organization_id=organization.id,
            community_id=community.id,
            user_id=user.id,
            issued_by=user.id,
            restriction_type=ModerationRestrictionType.SUSPENSION,
            reason="Reason.",
            starts_at=datetime.now(UTC) - timedelta(days=10),
            ends_at=datetime.now(UTC) - timedelta(days=1),
        )
        await repo.add(restriction)
        await db_session.commit()

        active = await repo.list_active_for_user(user.id)
        assert active == []

    async def test_scoped_to_community_when_given(self, db_session: AsyncSession) -> None:
        organization, user, community_a = await persist_org_user_community(db_session)
        community_b = await persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyModerationRestrictionRepository(db_session)
        restriction = ModerationRestriction.issue(
            organization_id=organization.id,
            community_id=community_a.id,
            user_id=user.id,
            issued_by=user.id,
            restriction_type=ModerationRestrictionType.WARNING,
            reason="Reason.",
        )
        await repo.add(restriction)
        await db_session.commit()

        active_in_b = await repo.list_active_for_user(user.id, community_id=community_b.id)
        assert active_in_b == []
        active_in_a = await repo.list_active_for_user(user.id, community_id=community_a.id)
        assert [r.id for r in active_in_a] == [restriction.id]


class TestListForUser:
    async def test_respects_cursor_pagination(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        repo = SqlAlchemyModerationRestrictionRepository(db_session)
        created = []
        for _ in range(3):
            restriction = ModerationRestriction.issue(
                organization_id=organization.id,
                community_id=community.id,
                user_id=user.id,
                issued_by=user.id,
                restriction_type=ModerationRestrictionType.WARNING,
                reason="Reason.",
            )
            await repo.add(restriction)
            await db_session.commit()
            created.append(restriction.id)

        first_page, next_cursor = await repo.list_for_user(user.id, limit=2)
        assert len(first_page) == 2
        assert next_cursor is not None

        second_page, second_cursor = await repo.list_for_user(user.id, cursor=next_cursor, limit=2)
        assert len(second_page) == 1
        assert second_cursor is None


class TestModerationRestrictionRequiresValidReferences:
    async def test_nonexistent_user_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, issuer = await persist_org_user(db_session)
        community = await persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyModerationRestrictionRepository(db_session)
        restriction = ModerationRestriction.issue(
            organization_id=organization.id,
            community_id=community.id,
            user_id=uuid4(),
            issued_by=issuer.id,
            restriction_type=ModerationRestrictionType.WARNING,
            reason="Reason.",
        )
        await repo.add(restriction)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
