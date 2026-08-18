"""Integration tests for `SqlAlchemySavedContentRepository` against a real
PostgreSQL instance: round-trip persistence, `get_saved`,
`list_by_user` (target_type filtering, cursor pagination), and the
`(user_id, target_type, target_id)` uniqueness constraint backing
"Prevent duplicate saves" as a concurrency safety net."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.community_engagement._helpers import persist_org_user

from app.modules.community_engagement.domain.entities import SavedContent
from app.modules.community_engagement.domain.enums import EngagementTargetType
from app.modules.community_engagement.infrastructure.repositories import (
    SqlAlchemySavedContentRepository,
)


class TestSavedContentRoundTrip:
    async def test_save_and_reload(self, db_session: AsyncSession) -> None:
        organization, user = await persist_org_user(db_session)
        repo = SqlAlchemySavedContentRepository(db_session)
        target_id = uuid4()
        saved = SavedContent.create(
            user_id=user.id,
            organization_id=organization.id,
            target_type=EngagementTargetType.ANSWER,
            target_id=target_id,
        )

        await repo.add(saved)
        await db_session.commit()

        reloaded = await repo.get_by_id(saved.id)
        assert reloaded is not None
        assert reloaded.user_id == user.id
        assert reloaded.target_type is EngagementTargetType.ANSWER
        assert reloaded.target_id == target_id


class TestGetSaved:
    async def test_returns_none_when_absent(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemySavedContentRepository(db_session)
        assert await repo.get_saved(uuid4(), EngagementTargetType.POST, uuid4()) is None

    async def test_returns_the_matching_row(self, db_session: AsyncSession) -> None:
        organization, user = await persist_org_user(db_session)
        repo = SqlAlchemySavedContentRepository(db_session)
        target_id = uuid4()
        saved = SavedContent.create(
            user_id=user.id,
            organization_id=organization.id,
            target_type=EngagementTargetType.POST,
            target_id=target_id,
        )
        await repo.add(saved)
        await db_session.commit()

        found = await repo.get_saved(user.id, EngagementTargetType.POST, target_id)
        assert found is not None
        assert found.id == saved.id


class TestListByUser:
    async def test_scopes_to_the_user(self, db_session: AsyncSession) -> None:
        organization, user = await persist_org_user(db_session)
        _, other_user = await persist_org_user(db_session)
        repo = SqlAlchemySavedContentRepository(db_session)

        mine = SavedContent.create(
            user_id=user.id,
            organization_id=organization.id,
            target_type=EngagementTargetType.POST,
            target_id=uuid4(),
        )
        theirs = SavedContent.create(
            user_id=other_user.id,
            organization_id=organization.id,
            target_type=EngagementTargetType.POST,
            target_id=uuid4(),
        )
        await repo.add(mine)
        await repo.add(theirs)
        await db_session.commit()

        results, _ = await repo.list_by_user(user.id)
        assert [s.id for s in results] == [mine.id]

    async def test_filters_by_target_type(self, db_session: AsyncSession) -> None:
        organization, user = await persist_org_user(db_session)
        repo = SqlAlchemySavedContentRepository(db_session)

        post_save = SavedContent.create(
            user_id=user.id,
            organization_id=organization.id,
            target_type=EngagementTargetType.POST,
            target_id=uuid4(),
        )
        answer_save = SavedContent.create(
            user_id=user.id,
            organization_id=organization.id,
            target_type=EngagementTargetType.ANSWER,
            target_id=uuid4(),
        )
        await repo.add(post_save)
        await repo.add(answer_save)
        await db_session.commit()

        results, _ = await repo.list_by_user(user.id, target_type=EngagementTargetType.ANSWER)
        assert [s.id for s in results] == [answer_save.id]

    async def test_respects_cursor_pagination(self, db_session: AsyncSession) -> None:
        organization, user = await persist_org_user(db_session)
        repo = SqlAlchemySavedContentRepository(db_session)
        created = []
        for _ in range(3):
            saved = SavedContent.create(
                user_id=user.id,
                organization_id=organization.id,
                target_type=EngagementTargetType.POST,
                target_id=uuid4(),
            )
            await repo.add(saved)
            await db_session.commit()
            created.append(saved.id)

        first_page, next_cursor = await repo.list_by_user(user.id, limit=2)
        assert len(first_page) == 2
        assert next_cursor is not None

        second_page, second_cursor = await repo.list_by_user(user.id, cursor=next_cursor, limit=2)
        assert len(second_page) == 1
        assert second_cursor is None

        all_ids = [s.id for s in first_page] + [s.id for s in second_page]
        assert set(all_ids) == set(created)


class TestRemove:
    async def test_removes_the_row(self, db_session: AsyncSession) -> None:
        organization, user = await persist_org_user(db_session)
        repo = SqlAlchemySavedContentRepository(db_session)
        saved = SavedContent.create(
            user_id=user.id,
            organization_id=organization.id,
            target_type=EngagementTargetType.POST,
            target_id=uuid4(),
        )
        await repo.add(saved)
        await db_session.commit()

        await repo.remove(saved.id)
        await db_session.commit()

        assert await repo.get_by_id(saved.id) is None

    async def test_is_a_no_op_when_the_row_is_already_gone(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemySavedContentRepository(db_session)
        await repo.remove(uuid4())  # must not raise
        await db_session.commit()


class TestUniqueUserTargetConstraint:
    async def test_duplicate_save_row_violates_the_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, user = await persist_org_user(db_session)
        repo = SqlAlchemySavedContentRepository(db_session)
        target_id = uuid4()

        first = SavedContent.create(
            user_id=user.id,
            organization_id=organization.id,
            target_type=EngagementTargetType.POST,
            target_id=target_id,
        )
        await repo.add(first)
        await db_session.commit()

        second = SavedContent.create(
            user_id=user.id,
            organization_id=organization.id,
            target_type=EngagementTargetType.POST,
            target_id=target_id,
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
