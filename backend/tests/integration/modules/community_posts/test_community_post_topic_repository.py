"""Integration tests for `SqlAlchemyCommunityPostTopicRepository` against
a real PostgreSQL instance."""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.community_posts._helpers import (
    persist_org_user_community,
    persist_topic,
)

from app.modules.community_posts.domain.entities import CommunityPost, CommunityPostTopic
from app.modules.community_posts.domain.value_objects import PostId, PostTitle
from app.modules.community_posts.infrastructure.repositories import (
    SqlAlchemyCommunityPostRepository,
    SqlAlchemyCommunityPostTopicRepository,
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


class TestCommunityPostTopicRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        post = await _persist_post(
            db_session,
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
        )
        topic = await persist_topic(db_session)
        repo = SqlAlchemyCommunityPostTopicRepository(db_session)
        assignment = CommunityPostTopic.create(post_id=PostId(post.id), topic_id=topic.id)

        await repo.add(assignment)
        await db_session.commit()

        reloaded = await repo.get_by_id(assignment.id)
        assert reloaded is not None
        assert reloaded.post_id.value == post.id
        assert reloaded.topic_id == topic.id

    async def test_get_by_id_returns_none_for_unknown_assignment(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyCommunityPostTopicRepository(db_session)
        assert await repo.get_by_id(uuid4()) is None

    async def test_remove_deletes_the_assignment(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        post = await _persist_post(
            db_session,
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
        )
        topic = await persist_topic(db_session)
        repo = SqlAlchemyCommunityPostTopicRepository(db_session)
        assignment = CommunityPostTopic.create(post_id=PostId(post.id), topic_id=topic.id)
        await repo.add(assignment)
        await db_session.commit()

        await repo.remove(assignment.id)
        await db_session.commit()

        assert await repo.get_by_id(assignment.id) is None


class TestCommunityPostTopicQueries:
    async def test_list_by_post_returns_assigned_topics(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        post = await _persist_post(
            db_session,
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
        )
        topic = await persist_topic(db_session)
        repo = SqlAlchemyCommunityPostTopicRepository(db_session)
        assignment = CommunityPostTopic.create(post_id=PostId(post.id), topic_id=topic.id)
        await repo.add(assignment)
        await db_session.commit()

        results = await repo.list_by_post(post.id)
        assert [a.topic_id for a in results] == [topic.id]

    async def test_list_post_ids_by_topic_returns_the_assigned_post(
        self, db_session: AsyncSession
    ) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        post = await _persist_post(
            db_session,
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
        )
        topic = await persist_topic(db_session)
        repo = SqlAlchemyCommunityPostTopicRepository(db_session)
        assignment = CommunityPostTopic.create(post_id=PostId(post.id), topic_id=topic.id)
        await repo.add(assignment)
        await db_session.commit()

        post_ids = await repo.list_post_ids_by_topic(topic.id)
        assert post.id in post_ids

    async def test_is_assigned_true_when_present(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        post = await _persist_post(
            db_session,
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
        )
        topic = await persist_topic(db_session)
        repo = SqlAlchemyCommunityPostTopicRepository(db_session)
        assignment = CommunityPostTopic.create(post_id=PostId(post.id), topic_id=topic.id)
        await repo.add(assignment)
        await db_session.commit()

        assert await repo.is_assigned(post.id, topic.id) is True

    async def test_is_assigned_false_when_absent(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityPostTopicRepository(db_session)
        assert await repo.is_assigned(uuid4(), uuid4()) is False
