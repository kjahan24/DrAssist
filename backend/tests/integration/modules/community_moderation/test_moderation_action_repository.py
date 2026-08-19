"""Integration tests for `SqlAlchemyModerationActionRepository` against a
real PostgreSQL instance: round-trip persistence, `get_latest_for_target`,
`list_for_target`/`list_for_actor` cursor pagination, and the absence of
any `remove()` method (immutable audit trail)."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.community_moderation._helpers import persist_org_user

from app.modules.community_moderation.domain.entities import ModerationAction
from app.modules.community_moderation.domain.enums import ModerationActionType, ModerationTargetType
from app.modules.community_moderation.domain.repositories import ModerationActionRepository
from app.modules.community_moderation.infrastructure.repositories import (
    SqlAlchemyModerationActionRepository,
)


class TestModerationActionRoundTrip:
    async def test_save_and_reload(self, db_session: AsyncSession) -> None:
        organization, user = await persist_org_user(db_session)
        repo = SqlAlchemyModerationActionRepository(db_session)
        target_id = uuid4()
        action = ModerationAction.record(
            organization_id=organization.id,
            actor_id=user.id,
            action_type=ModerationActionType.REMOVE,
            target_type=ModerationTargetType.POST,
            target_id=target_id,
            reason="Medical misinformation.",
            previous_state="active",
            new_state="removed",
        )

        await repo.add(action)
        await db_session.commit()

        reloaded = await repo.get_by_id(action.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.actor_id == user.id
        assert reloaded.action_type is ModerationActionType.REMOVE
        assert reloaded.target_id == target_id
        assert reloaded.reason == "Medical misinformation."
        assert reloaded.previous_state == "active"
        assert reloaded.new_state == "removed"


class TestGetLatestForTarget:
    async def test_returns_none_when_no_actions_exist(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyModerationActionRepository(db_session)
        result = await repo.get_latest_for_target(ModerationTargetType.POST, uuid4())
        assert result is None

    async def test_returns_the_most_recent_action(self, db_session: AsyncSession) -> None:
        organization, user = await persist_org_user(db_session)
        repo = SqlAlchemyModerationActionRepository(db_session)
        target_id = uuid4()

        first = ModerationAction.record(
            organization_id=organization.id,
            actor_id=user.id,
            action_type=ModerationActionType.REMOVE,
            target_type=ModerationTargetType.POST,
            target_id=target_id,
            reason="Removed.",
            previous_state="active",
            new_state="removed",
        )
        await repo.add(first)
        await db_session.commit()

        second = ModerationAction.record(
            organization_id=organization.id,
            actor_id=user.id,
            action_type=ModerationActionType.RESTORE,
            target_type=ModerationTargetType.POST,
            target_id=target_id,
            reason="Restored.",
            previous_state="removed",
            new_state="active",
        )
        await repo.add(second)
        await db_session.commit()

        latest = await repo.get_latest_for_target(ModerationTargetType.POST, target_id)
        assert latest is not None
        assert latest.id == second.id


class TestListForTargetAndActor:
    async def test_list_for_target_scopes_correctly(self, db_session: AsyncSession) -> None:
        organization, user = await persist_org_user(db_session)
        repo = SqlAlchemyModerationActionRepository(db_session)
        target_a, target_b = uuid4(), uuid4()

        action_a = ModerationAction.record(
            organization_id=organization.id,
            actor_id=user.id,
            action_type=ModerationActionType.LOCK,
            target_type=ModerationTargetType.COMMENT,
            target_id=target_a,
            reason="Locked.",
        )
        action_b = ModerationAction.record(
            organization_id=organization.id,
            actor_id=user.id,
            action_type=ModerationActionType.LOCK,
            target_type=ModerationTargetType.COMMENT,
            target_id=target_b,
            reason="Locked.",
        )
        await repo.add(action_a)
        await repo.add(action_b)
        await db_session.commit()

        results, _ = await repo.list_for_target(ModerationTargetType.COMMENT, target_a)
        assert [a.id for a in results] == [action_a.id]

    async def test_list_for_actor_scopes_correctly(self, db_session: AsyncSession) -> None:
        organization, actor = await persist_org_user(db_session)
        _, other_actor = await persist_org_user(db_session)
        repo = SqlAlchemyModerationActionRepository(db_session)

        mine = ModerationAction.record(
            organization_id=organization.id,
            actor_id=actor.id,
            action_type=ModerationActionType.APPROVE,
            target_type=ModerationTargetType.POST,
            target_id=uuid4(),
            reason="Reviewed.",
        )
        theirs = ModerationAction.record(
            organization_id=organization.id,
            actor_id=other_actor.id,
            action_type=ModerationActionType.APPROVE,
            target_type=ModerationTargetType.POST,
            target_id=uuid4(),
            reason="Reviewed.",
        )
        await repo.add(mine)
        await repo.add(theirs)
        await db_session.commit()

        results, _ = await repo.list_for_actor(actor.id)
        assert [a.id for a in results] == [mine.id]

    async def test_respects_cursor_pagination(self, db_session: AsyncSession) -> None:
        organization, user = await persist_org_user(db_session)
        repo = SqlAlchemyModerationActionRepository(db_session)
        target_id = uuid4()
        created = []
        for _ in range(3):
            action = ModerationAction.record(
                organization_id=organization.id,
                actor_id=user.id,
                action_type=ModerationActionType.APPROVE,
                target_type=ModerationTargetType.POST,
                target_id=target_id,
                reason="Reviewed.",
            )
            await repo.add(action)
            await db_session.commit()
            created.append(action.id)

        first_page, next_cursor = await repo.list_for_target(
            ModerationTargetType.POST, target_id, limit=2
        )
        assert len(first_page) == 2
        assert next_cursor is not None

        second_page, second_cursor = await repo.list_for_target(
            ModerationTargetType.POST, target_id, cursor=next_cursor, limit=2
        )
        assert len(second_page) == 1
        assert second_cursor is None


class TestModerationActionRequiresValidReferences:
    async def test_nonexistent_actor_id_violates_fk_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, _ = await persist_org_user(db_session)
        repo = SqlAlchemyModerationActionRepository(db_session)
        action = ModerationAction.record(
            organization_id=organization.id,
            actor_id=uuid4(),
            action_type=ModerationActionType.REMOVE,
            target_type=ModerationTargetType.POST,
            target_id=uuid4(),
            reason="Reason.",
        )
        await repo.add(action)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestModerationActionRepositoryHasNoRemoveMethod:
    def test_repository_interface_has_no_remove_method(self) -> None:
        """Structural confirmation of `domain/repositories.py`'s own
        docstring: "Never delete audit history through normal APIs" is
        enforced by this port simply not offering a way to."""
        assert not hasattr(ModerationActionRepository, "remove")
