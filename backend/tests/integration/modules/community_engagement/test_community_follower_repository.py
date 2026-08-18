"""Integration tests for `SqlAlchemyCommunityFollowerRepository` against a
real PostgreSQL instance: round-trip persistence, `get_follow`,
`list_followers`/`list_following` cursor pagination, `count_followers`,
and the `(user_id, community_id)` uniqueness constraint backing "Prevent
duplicate follows" as a concurrency safety net."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.community_engagement._helpers import (
    persist_community,
    persist_org_user,
)

from app.modules.community_engagement.domain.entities import CommunityFollower
from app.modules.community_engagement.infrastructure.repositories import (
    SqlAlchemyCommunityFollowerRepository,
)


class TestCommunityFollowerRoundTrip:
    async def test_save_and_reload(self, db_session: AsyncSession) -> None:
        organization, user = await persist_org_user(db_session)
        community = await persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityFollowerRepository(db_session)

        follower = CommunityFollower.create(
            user_id=user.id, organization_id=organization.id, community_id=community.id
        )
        await repo.add(follower)
        await db_session.commit()

        reloaded = await repo.get_by_id(follower.id)
        assert reloaded is not None
        assert reloaded.user_id == user.id
        assert reloaded.community_id == community.id


class TestGetFollow:
    async def test_returns_none_when_absent(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityFollowerRepository(db_session)
        assert await repo.get_follow(uuid4(), uuid4()) is None

    async def test_returns_the_matching_row(self, db_session: AsyncSession) -> None:
        organization, user = await persist_org_user(db_session)
        community = await persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityFollowerRepository(db_session)
        follower = CommunityFollower.create(
            user_id=user.id, organization_id=organization.id, community_id=community.id
        )
        await repo.add(follower)
        await db_session.commit()

        found = await repo.get_follow(user.id, community.id)
        assert found is not None
        assert found.id == follower.id


class TestListFollowersAndFollowing:
    async def test_list_followers_scopes_to_the_community(self, db_session: AsyncSession) -> None:
        organization, user_a = await persist_org_user(db_session)
        _, user_b = await persist_org_user(db_session)
        community_a = await persist_community(db_session, organization_id=organization.id)
        community_b = await persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityFollowerRepository(db_session)

        follow_a = CommunityFollower.create(
            user_id=user_a.id, organization_id=organization.id, community_id=community_a.id
        )
        follow_b = CommunityFollower.create(
            user_id=user_b.id, organization_id=organization.id, community_id=community_b.id
        )
        await repo.add(follow_a)
        await repo.add(follow_b)
        await db_session.commit()

        results, _ = await repo.list_followers(community_a.id)
        assert [f.id for f in results] == [follow_a.id]

    async def test_list_following_scopes_to_the_user(self, db_session: AsyncSession) -> None:
        organization, user = await persist_org_user(db_session)
        community_a = await persist_community(db_session, organization_id=organization.id)
        community_b = await persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityFollowerRepository(db_session)

        follow_a = CommunityFollower.create(
            user_id=user.id, organization_id=organization.id, community_id=community_a.id
        )
        await repo.add(follow_a)
        await db_session.commit()
        follow_b = CommunityFollower.create(
            user_id=user.id, organization_id=organization.id, community_id=community_b.id
        )
        await repo.add(follow_b)
        await db_session.commit()

        results, _ = await repo.list_following(user.id)
        assert {f.id for f in results} == {follow_a.id, follow_b.id}

    async def test_respects_cursor_pagination(self, db_session: AsyncSession) -> None:
        organization, _ = await persist_org_user(db_session)
        community = await persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityFollowerRepository(db_session)
        created = []
        for _ in range(3):
            _, follower_user = await persist_org_user(db_session)
            follow = CommunityFollower.create(
                user_id=follower_user.id,
                organization_id=organization.id,
                community_id=community.id,
            )
            await repo.add(follow)
            await db_session.commit()
            created.append(follow.id)

        first_page, next_cursor = await repo.list_followers(community.id, limit=2)
        assert len(first_page) == 2
        assert next_cursor is not None

        second_page, second_cursor = await repo.list_followers(
            community.id, cursor=next_cursor, limit=2
        )
        assert len(second_page) == 1
        assert second_cursor is None


class TestCountFollowers:
    async def test_counts_followers_of_the_community(self, db_session: AsyncSession) -> None:
        organization, _ = await persist_org_user(db_session)
        community = await persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityFollowerRepository(db_session)
        for _ in range(3):
            _, follower_user = await persist_org_user(db_session)
            await repo.add(
                CommunityFollower.create(
                    user_id=follower_user.id,
                    organization_id=organization.id,
                    community_id=community.id,
                )
            )
        await db_session.commit()

        assert await repo.count_followers(community.id) == 3

    async def test_returns_zero_for_a_community_with_no_followers(
        self, db_session: AsyncSession
    ) -> None:
        organization, _ = await persist_org_user(db_session)
        community = await persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityFollowerRepository(db_session)
        assert await repo.count_followers(community.id) == 0


class TestRemove:
    async def test_removes_the_row(self, db_session: AsyncSession) -> None:
        organization, user = await persist_org_user(db_session)
        community = await persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityFollowerRepository(db_session)
        follower = CommunityFollower.create(
            user_id=user.id, organization_id=organization.id, community_id=community.id
        )
        await repo.add(follower)
        await db_session.commit()

        await repo.remove(follower.id)
        await db_session.commit()

        assert await repo.get_by_id(follower.id) is None

    async def test_is_a_no_op_when_the_row_is_already_gone(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityFollowerRepository(db_session)
        await repo.remove(uuid4())  # must not raise
        await db_session.commit()


class TestUniqueUserCommunityConstraint:
    async def test_duplicate_follow_row_violates_the_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, user = await persist_org_user(db_session)
        community = await persist_community(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityFollowerRepository(db_session)

        first = CommunityFollower.create(
            user_id=user.id, organization_id=organization.id, community_id=community.id
        )
        await repo.add(first)
        await db_session.commit()

        second = CommunityFollower.create(
            user_id=user.id, organization_id=organization.id, community_id=community.id
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
