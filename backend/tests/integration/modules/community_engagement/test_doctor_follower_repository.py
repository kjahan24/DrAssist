"""Integration tests for `SqlAlchemyDoctorFollowerRepository` against a
real PostgreSQL instance: round-trip persistence, `get_follow`,
`list_followers`/`list_following` cursor pagination, `count_followers`,
the `(follower_user_id, followed_user_id)` uniqueness constraint, and the
`ck_doctor_followers_no_self_follow` CHECK constraint backing "Users
cannot follow themselves" as a database-level safety net underneath
`FollowDoctorService`'s own application-layer check."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.community_engagement._helpers import persist_org_user

from app.modules.community_engagement.domain.entities import DoctorFollower
from app.modules.community_engagement.infrastructure.repositories import (
    SqlAlchemyDoctorFollowerRepository,
)


class TestDoctorFollowerRoundTrip:
    async def test_save_and_reload(self, db_session: AsyncSession) -> None:
        organization, follower_user = await persist_org_user(db_session)
        _, followed_user = await persist_org_user(db_session)
        repo = SqlAlchemyDoctorFollowerRepository(db_session)

        follower = DoctorFollower.create(
            follower_user_id=follower_user.id,
            organization_id=organization.id,
            followed_user_id=followed_user.id,
        )
        await repo.add(follower)
        await db_session.commit()

        reloaded = await repo.get_by_id(follower.id)
        assert reloaded is not None
        assert reloaded.follower_user_id == follower_user.id
        assert reloaded.followed_user_id == followed_user.id


class TestGetFollow:
    async def test_returns_none_when_absent(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyDoctorFollowerRepository(db_session)
        assert await repo.get_follow(uuid4(), uuid4()) is None

    async def test_returns_the_matching_row(self, db_session: AsyncSession) -> None:
        organization, follower_user = await persist_org_user(db_session)
        _, followed_user = await persist_org_user(db_session)
        repo = SqlAlchemyDoctorFollowerRepository(db_session)
        follower = DoctorFollower.create(
            follower_user_id=follower_user.id,
            organization_id=organization.id,
            followed_user_id=followed_user.id,
        )
        await repo.add(follower)
        await db_session.commit()

        found = await repo.get_follow(follower_user.id, followed_user.id)
        assert found is not None
        assert found.id == follower.id


class TestListFollowersAndFollowing:
    async def test_list_followers_scopes_to_the_followed_user(
        self, db_session: AsyncSession
    ) -> None:
        organization, follower_a = await persist_org_user(db_session)
        _, follower_b = await persist_org_user(db_session)
        _, followed_a = await persist_org_user(db_session)
        _, followed_b = await persist_org_user(db_session)
        repo = SqlAlchemyDoctorFollowerRepository(db_session)

        follow_a = DoctorFollower.create(
            follower_user_id=follower_a.id,
            organization_id=organization.id,
            followed_user_id=followed_a.id,
        )
        follow_b = DoctorFollower.create(
            follower_user_id=follower_b.id,
            organization_id=organization.id,
            followed_user_id=followed_b.id,
        )
        await repo.add(follow_a)
        await repo.add(follow_b)
        await db_session.commit()

        results, _ = await repo.list_followers(followed_a.id)
        assert [f.id for f in results] == [follow_a.id]

    async def test_list_following_scopes_to_the_follower_user(
        self, db_session: AsyncSession
    ) -> None:
        organization, follower_user = await persist_org_user(db_session)
        _, followed_a = await persist_org_user(db_session)
        _, followed_b = await persist_org_user(db_session)
        repo = SqlAlchemyDoctorFollowerRepository(db_session)

        follow_a = DoctorFollower.create(
            follower_user_id=follower_user.id,
            organization_id=organization.id,
            followed_user_id=followed_a.id,
        )
        await repo.add(follow_a)
        await db_session.commit()
        follow_b = DoctorFollower.create(
            follower_user_id=follower_user.id,
            organization_id=organization.id,
            followed_user_id=followed_b.id,
        )
        await repo.add(follow_b)
        await db_session.commit()

        results, _ = await repo.list_following(follower_user.id)
        assert {f.id for f in results} == {follow_a.id, follow_b.id}

    async def test_respects_cursor_pagination(self, db_session: AsyncSession) -> None:
        organization, followed_user = await persist_org_user(db_session)
        repo = SqlAlchemyDoctorFollowerRepository(db_session)
        created = []
        for _ in range(3):
            _, follower_user = await persist_org_user(db_session)
            follow = DoctorFollower.create(
                follower_user_id=follower_user.id,
                organization_id=organization.id,
                followed_user_id=followed_user.id,
            )
            await repo.add(follow)
            await db_session.commit()
            created.append(follow.id)

        first_page, next_cursor = await repo.list_followers(followed_user.id, limit=2)
        assert len(first_page) == 2
        assert next_cursor is not None

        second_page, second_cursor = await repo.list_followers(
            followed_user.id, cursor=next_cursor, limit=2
        )
        assert len(second_page) == 1
        assert second_cursor is None


class TestCountFollowers:
    async def test_counts_followers_of_the_user(self, db_session: AsyncSession) -> None:
        organization, followed_user = await persist_org_user(db_session)
        repo = SqlAlchemyDoctorFollowerRepository(db_session)
        for _ in range(3):
            _, follower_user = await persist_org_user(db_session)
            await repo.add(
                DoctorFollower.create(
                    follower_user_id=follower_user.id,
                    organization_id=organization.id,
                    followed_user_id=followed_user.id,
                )
            )
        await db_session.commit()

        assert await repo.count_followers(followed_user.id) == 3

    async def test_returns_zero_for_a_user_with_no_followers(
        self, db_session: AsyncSession
    ) -> None:
        _, followed_user = await persist_org_user(db_session)
        repo = SqlAlchemyDoctorFollowerRepository(db_session)
        assert await repo.count_followers(followed_user.id) == 0


class TestRemove:
    async def test_removes_the_row(self, db_session: AsyncSession) -> None:
        organization, follower_user = await persist_org_user(db_session)
        _, followed_user = await persist_org_user(db_session)
        repo = SqlAlchemyDoctorFollowerRepository(db_session)
        follower = DoctorFollower.create(
            follower_user_id=follower_user.id,
            organization_id=organization.id,
            followed_user_id=followed_user.id,
        )
        await repo.add(follower)
        await db_session.commit()

        await repo.remove(follower.id)
        await db_session.commit()

        assert await repo.get_by_id(follower.id) is None

    async def test_is_a_no_op_when_the_row_is_already_gone(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyDoctorFollowerRepository(db_session)
        await repo.remove(uuid4())  # must not raise
        await db_session.commit()


class TestUniqueFollowerFollowedConstraint:
    async def test_duplicate_follow_row_violates_the_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, follower_user = await persist_org_user(db_session)
        _, followed_user = await persist_org_user(db_session)
        repo = SqlAlchemyDoctorFollowerRepository(db_session)

        first = DoctorFollower.create(
            follower_user_id=follower_user.id,
            organization_id=organization.id,
            followed_user_id=followed_user.id,
        )
        await repo.add(first)
        await db_session.commit()

        second = DoctorFollower.create(
            follower_user_id=follower_user.id,
            organization_id=organization.id,
            followed_user_id=followed_user.id,
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestSelfFollowCheckConstraint:
    async def test_self_follow_row_violates_the_check_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization, user = await persist_org_user(db_session)
        repo = SqlAlchemyDoctorFollowerRepository(db_session)

        follower = DoctorFollower.create(
            follower_user_id=user.id, organization_id=organization.id, followed_user_id=user.id
        )
        await repo.add(follower)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
