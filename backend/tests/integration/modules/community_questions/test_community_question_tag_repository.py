"""Integration tests for `SqlAlchemyCommunityQuestionTagRepository`
against a real PostgreSQL instance."""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.community_questions._helpers import (
    persist_org_user_community,
    persist_topic,
)

from app.modules.community_questions.domain.entities import CommunityQuestion, CommunityQuestionTag
from app.modules.community_questions.domain.value_objects import QuestionId, QuestionTitle
from app.modules.community_questions.infrastructure.repositories import (
    SqlAlchemyCommunityQuestionRepository,
    SqlAlchemyCommunityQuestionTagRepository,
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


class TestCommunityQuestionTagRoundTrip:
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
        repo = SqlAlchemyCommunityQuestionTagRepository(db_session)
        assignment = CommunityQuestionTag.create(
            question_id=QuestionId(question.id), tag="Oncology"
        )

        await repo.add(assignment)
        await db_session.commit()

        reloaded = await repo.get_by_id(assignment.id)
        assert reloaded is not None
        assert reloaded.question_id.value == question.id
        assert reloaded.tag == "oncology"

    async def test_get_by_id_returns_none_for_unknown_assignment(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyCommunityQuestionTagRepository(db_session)
        assert await repo.get_by_id(uuid4()) is None

    async def test_remove_deletes_the_assignment(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        topic = await persist_topic(db_session)
        question = await _persist_question(
            db_session,
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=topic.id,
        )
        repo = SqlAlchemyCommunityQuestionTagRepository(db_session)
        assignment = CommunityQuestionTag.create(
            question_id=QuestionId(question.id), tag="oncology"
        )
        await repo.add(assignment)
        await db_session.commit()

        await repo.remove(assignment.id)
        await db_session.commit()

        assert await repo.get_by_id(assignment.id) is None


class TestCommunityQuestionTagQueries:
    async def test_list_by_question_returns_assigned_tags(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        topic = await persist_topic(db_session)
        question = await _persist_question(
            db_session,
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=topic.id,
        )
        repo = SqlAlchemyCommunityQuestionTagRepository(db_session)
        assignment = CommunityQuestionTag.create(
            question_id=QuestionId(question.id), tag="oncology"
        )
        await repo.add(assignment)
        await db_session.commit()

        results = await repo.list_by_question(question.id)
        assert [a.tag for a in results] == ["oncology"]

    async def test_is_assigned_true_when_present(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        topic = await persist_topic(db_session)
        question = await _persist_question(
            db_session,
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            primary_topic_id=topic.id,
        )
        repo = SqlAlchemyCommunityQuestionTagRepository(db_session)
        assignment = CommunityQuestionTag.create(
            question_id=QuestionId(question.id), tag="oncology"
        )
        await repo.add(assignment)
        await db_session.commit()

        assert await repo.is_assigned(question.id, "Oncology") is True

    async def test_is_assigned_false_when_absent(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityQuestionTagRepository(db_session)
        assert await repo.is_assigned(uuid4(), "oncology") is False
