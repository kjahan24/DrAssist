"""Integration tests for `SqlAlchemyCommunityPostTagRepository` against a
real PostgreSQL instance."""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.community_posts._helpers import persist_org_user_community

from app.modules.community_posts.domain.entities import CommunityPost, CommunityPostTag
from app.modules.community_posts.domain.value_objects import PostId, PostTitle
from app.modules.community_posts.infrastructure.repositories import (
    SqlAlchemyCommunityPostRepository,
    SqlAlchemyCommunityPostTagRepository,
)


async def _persist_post(
    db_session: AsyncSession, *, community_id: object, organization_id: object, author_id: object
) -> CommunityPost:
    posts_repo = SqlAlchemyCommunityPostRepository(db_session)
    post = CommunityPost.create(
        community_id=community_id,  # type: ignore[arg-type]
        organization_id=organization_id,  # type: ignore[arg-type]
        author_id=author_id,  # type: ignore[arg-type]
        title=PostTitle("Title"),
        body="Body",
    )
    await posts_repo.add(post)
    await db_session.commit()
    return post


class TestCommunityPostTagRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        post = await _persist_post(
            db_session,
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
        )
        repo = SqlAlchemyCommunityPostTagRepository(db_session)
        assignment = CommunityPostTag.create(post_id=PostId(post.id), tag="Oncology")

        await repo.add(assignment)
        await db_session.commit()

        reloaded = await repo.get_by_id(assignment.id)
        assert reloaded is not None
        assert reloaded.post_id.value == post.id
        assert reloaded.tag == "oncology"

    async def test_get_by_id_returns_none_for_unknown_assignment(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyCommunityPostTagRepository(db_session)
        assert await repo.get_by_id(uuid4()) is None

    async def test_remove_deletes_the_assignment(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        post = await _persist_post(
            db_session,
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
        )
        repo = SqlAlchemyCommunityPostTagRepository(db_session)
        assignment = CommunityPostTag.create(post_id=PostId(post.id), tag="oncology")
        await repo.add(assignment)
        await db_session.commit()

        await repo.remove(assignment.id)
        await db_session.commit()

        assert await repo.get_by_id(assignment.id) is None


class TestCommunityPostTagQueries:
    async def test_list_by_post_returns_assigned_tags(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        post = await _persist_post(
            db_session,
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
        )
        repo = SqlAlchemyCommunityPostTagRepository(db_session)
        assignment = CommunityPostTag.create(post_id=PostId(post.id), tag="oncology")
        await repo.add(assignment)
        await db_session.commit()

        results = await repo.list_by_post(post.id)
        assert [a.tag for a in results] == ["oncology"]

    async def test_is_assigned_true_when_present(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        post = await _persist_post(
            db_session,
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
        )
        repo = SqlAlchemyCommunityPostTagRepository(db_session)
        assignment = CommunityPostTag.create(post_id=PostId(post.id), tag="oncology")
        await repo.add(assignment)
        await db_session.commit()

        assert await repo.is_assigned(post.id, "Oncology") is True

    async def test_is_assigned_false_when_absent(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityPostTagRepository(db_session)
        assert await repo.is_assigned(uuid4(), "oncology") is False
