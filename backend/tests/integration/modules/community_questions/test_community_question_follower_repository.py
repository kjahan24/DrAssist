"""Integration tests for `SqlAlchemyCommunityQuestionFollowerRepository`
against a real PostgreSQL instance."""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.community_questions._helpers import (
    persist_org_user_community,
    persist_topic,
    persist_user,
)

from app.modules.community_questions.domain.entities import (
    CommunityQuestion,
    CommunityQuestionFollower,
)
from app.modules.community_questions.domain.value_objects import QuestionId, QuestionTitle
from app.modules.community_questions.infrastructure.repositories import (
    SqlAlchemyCommunityQuestionFollowerRepository,
    SqlAlchemyCommunityQuestionRepository,
)


async def _persist_question(
    db_session: AsyncSession,
    *,
    community_id: object,
    organization_id: object,
    author_id: object,
    primary_topic_id: object,
) -> CommunityQuestion:
    questions_repo = SqlAlchemyCommunityQuestionRepository(db_session)
    question = CommunityQuestion.create(
        community_id=community_id,  # type: ignore[arg-type]
        organization_id=organization_id,  # type: ignore[arg-type]
        author_id=author_id,  # type: ignore[arg-type]
        primary_topic_id=primary_topic_id,  # type: ignore[arg-type]
        title=QuestionTitle("Title"),
        body="Body",
    )
    await questions_repo.add(question)
    await db_session.commit()
    return question


class TestCommunityQuestionFollowerRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        topic = await persist_topic(db_session)
        question = await _persist_question(
            db_session,
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=topic.id,
        )
        follower_user = await persist_user(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityQuestionFollowerRepository(db_session)
        follower = CommunityQuestionFollower.create(
            question_id=QuestionId(question.id), user_id=follower_user.id
        )

        await repo.add(follower)
        await db_session.commit()

        reloaded = await repo.get_by_id(follower.id)
        assert reloaded is not None
        assert reloaded.question_id.value == question.id
        assert reloaded.user_id == follower_user.id

    async def test_get_by_id_returns_none_for_unknown_follower(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyCommunityQuestionFollowerRepository(db_session)
        assert await repo.get_by_id(uuid4()) is None

    async def test_remove_deletes_the_follower(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        topic = await persist_topic(db_session)
        question = await _persist_question(
            db_session,
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=topic.id,
        )
        follower_user = await persist_user(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityQuestionFollowerRepository(db_session)
        follower = CommunityQuestionFollower.create(
            question_id=QuestionId(question.id), user_id=follower_user.id
        )
        await repo.add(follower)
        await db_session.commit()

        await repo.remove(follower.id)
        await db_session.commit()

        assert await repo.get_by_id(follower.id) is None


class TestCommunityQuestionFollowerQueries:
    async def test_get_by_question_and_user_finds_the_matching_follower(
        self, db_session: AsyncSession
    ) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        topic = await persist_topic(db_session)
        question = await _persist_question(
            db_session,
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=topic.id,
        )
        follower_user = await persist_user(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityQuestionFollowerRepository(db_session)
        follower = CommunityQuestionFollower.create(
            question_id=QuestionId(question.id), user_id=follower_user.id
        )
        await repo.add(follower)
        await db_session.commit()

        reloaded = await repo.get_by_question_and_user(question.id, follower_user.id)
        assert reloaded is not None
        assert reloaded.id == follower.id

    async def test_get_by_question_and_user_returns_none_when_absent(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyCommunityQuestionFollowerRepository(db_session)
        assert await repo.get_by_question_and_user(uuid4(), uuid4()) is None

    async def test_list_by_question_returns_followers(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        topic = await persist_topic(db_session)
        question = await _persist_question(
            db_session,
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=topic.id,
        )
        follower_user = await persist_user(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityQuestionFollowerRepository(db_session)
        follower = CommunityQuestionFollower.create(
            question_id=QuestionId(question.id), user_id=follower_user.id
        )
        await repo.add(follower)
        await db_session.commit()

        results = await repo.list_by_question(question.id)
        assert [f.user_id for f in results] == [follower_user.id]

    async def test_is_following_true_when_present(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        topic = await persist_topic(db_session)
        question = await _persist_question(
            db_session,
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=topic.id,
        )
        follower_user = await persist_user(db_session, organization_id=organization.id)
        repo = SqlAlchemyCommunityQuestionFollowerRepository(db_session)
        follower = CommunityQuestionFollower.create(
            question_id=QuestionId(question.id), user_id=follower_user.id
        )
        await repo.add(follower)
        await db_session.commit()

        assert await repo.is_following(question.id, follower_user.id) is True

    async def test_is_following_false_when_absent(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityQuestionFollowerRepository(db_session)
        assert await repo.is_following(uuid4(), uuid4()) is False
