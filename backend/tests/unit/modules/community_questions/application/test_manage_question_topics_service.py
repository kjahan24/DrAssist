"""Unit tests for `ManageQuestionTopicsService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityRole
from app.modules.community_questions.application.dto import (
    AssignQuestionTopicInput,
    UnassignQuestionTopicInput,
)
from app.modules.community_questions.application.services.manage_question_topics_service import (
    ManageQuestionTopicsService,
)
from app.modules.community_questions.domain.entities import CommunityQuestion
from app.modules.community_questions.domain.events import CommunityQuestionTopicAssigned
from app.modules.community_questions.domain.exceptions import (
    DuplicateQuestionTopicError,
    InsufficientQuestionRoleError,
    QuestionNotFoundError,
    QuestionTopicNotFoundError,
    TopicNotFoundForQuestionError,
)
from app.modules.community_questions.domain.value_objects import QuestionTitle
from tests.unit.modules.community_questions.application.fakes import (
    FakeCommunityQueryPort,
    FakeCommunityQuestionRepository,
    FakeCommunityQuestionTopicRepository,
    FakeTopicQueryPort,
    FakeUnitOfWork,
    make_community_summary,
    make_member_summary,
)


def _seeded() -> (
    tuple[
        ManageQuestionTopicsService,
        FakeCommunityQuestionRepository,
        FakeCommunityQuestionTopicRepository,
        FakeCommunityQueryPort,
        FakeTopicQueryPort,
        FakeUnitOfWork,
    ]
):
    questions = FakeCommunityQuestionRepository()
    question_topics = FakeCommunityQuestionTopicRepository()
    communities = FakeCommunityQueryPort()
    topics = FakeTopicQueryPort()
    uow = FakeUnitOfWork()
    service = ManageQuestionTopicsService(
        question_topic_repository=question_topics,
        question_repository=questions,
        community_query_port=communities,
        topic_query_port=topics,
        unit_of_work=uow,
    )
    return service, questions, question_topics, communities, topics, uow


async def _seed_question(
    questions: FakeCommunityQuestionRepository, communities: FakeCommunityQueryPort
) -> CommunityQuestion:
    question = CommunityQuestion.create(
        community_id=uuid4(),
        organization_id=uuid4(),
        author_id=uuid4(),
        primary_topic_id=uuid4(),
        title=QuestionTitle("Title"),
        body="Body",
    )
    await questions.add(question)
    communities.add_community(make_community_summary(community_id=question.community_id))
    return question


class TestAssignTopic:
    async def test_author_assigns_a_secondary_topic(self) -> None:
        service, questions, question_topics, communities, topics, _ = _seeded()
        question = await _seed_question(questions, communities)
        topic_id = uuid4()
        topics.add_topic(topic_id)

        summary = await service.assign_topic(
            AssignQuestionTopicInput(
                question_id=question.id, acting_user_id=question.author_id, topic_id=topic_id
            )
        )
        assert summary.topic_id == topic_id
        assert len(await question_topics.list_by_question(question.id)) == 1

    async def test_plain_member_cannot_assign_topic_to_someone_elses_question(self) -> None:
        service, questions, _, communities, topics, _ = _seeded()
        question = await _seed_question(questions, communities)
        topic_id = uuid4()
        topics.add_topic(topic_id)
        member_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=question.community_id, user_id=member_id, role=CommunityRole.MEMBER
            )
        )

        with pytest.raises(InsufficientQuestionRoleError):
            await service.assign_topic(
                AssignQuestionTopicInput(
                    question_id=question.id, acting_user_id=member_id, topic_id=topic_id
                )
            )

    async def test_unknown_question_raises(self) -> None:
        service, _, _, _, topics, _ = _seeded()
        topic_id = uuid4()
        topics.add_topic(topic_id)
        with pytest.raises(QuestionNotFoundError):
            await service.assign_topic(
                AssignQuestionTopicInput(
                    question_id=uuid4(), acting_user_id=uuid4(), topic_id=topic_id
                )
            )

    async def test_unknown_topic_raises(self) -> None:
        service, questions, _, communities, _, _ = _seeded()
        question = await _seed_question(questions, communities)

        with pytest.raises(TopicNotFoundForQuestionError):
            await service.assign_topic(
                AssignQuestionTopicInput(
                    question_id=question.id, acting_user_id=question.author_id, topic_id=uuid4()
                )
            )

    async def test_duplicate_assignment_raises(self) -> None:
        service, questions, _, communities, topics, _ = _seeded()
        question = await _seed_question(questions, communities)
        topic_id = uuid4()
        topics.add_topic(topic_id)
        await service.assign_topic(
            AssignQuestionTopicInput(
                question_id=question.id, acting_user_id=question.author_id, topic_id=topic_id
            )
        )

        with pytest.raises(DuplicateQuestionTopicError):
            await service.assign_topic(
                AssignQuestionTopicInput(
                    question_id=question.id, acting_user_id=question.author_id, topic_id=topic_id
                )
            )

    async def test_assigning_the_primary_topic_as_secondary_raises(self) -> None:
        service, questions, _, communities, topics, _ = _seeded()
        question = await _seed_question(questions, communities)
        topics.add_topic(question.primary_topic_id)

        with pytest.raises(DuplicateQuestionTopicError):
            await service.assign_topic(
                AssignQuestionTopicInput(
                    question_id=question.id,
                    acting_user_id=question.author_id,
                    topic_id=question.primary_topic_id,
                )
            )

    async def test_commits_and_publishes_event(self) -> None:
        service, questions, _, communities, topics, uow = _seeded()
        question = await _seed_question(questions, communities)
        topic_id = uuid4()
        topics.add_topic(topic_id)

        await service.assign_topic(
            AssignQuestionTopicInput(
                question_id=question.id, acting_user_id=question.author_id, topic_id=topic_id
            )
        )
        assert uow.committed is True
        assert any(isinstance(e, CommunityQuestionTopicAssigned) for e in uow.published_events)


class TestListTopics:
    async def test_lists_assigned_topics(self) -> None:
        service, questions, _, communities, topics, _ = _seeded()
        question = await _seed_question(questions, communities)
        topic_id = uuid4()
        topics.add_topic(topic_id)
        await service.assign_topic(
            AssignQuestionTopicInput(
                question_id=question.id, acting_user_id=question.author_id, topic_id=topic_id
            )
        )

        result = await service.list_topics(question.id)
        assert [t.topic_id for t in result] == [topic_id]

    async def test_returns_empty_for_a_question_with_no_secondary_topics(self) -> None:
        service, questions, _, communities, _, _ = _seeded()
        question = await _seed_question(questions, communities)

        assert await service.list_topics(question.id) == []


class TestUnassignTopic:
    async def test_author_unassigns_a_topic(self) -> None:
        service, questions, _, communities, topics, _ = _seeded()
        question = await _seed_question(questions, communities)
        topic_id = uuid4()
        topics.add_topic(topic_id)
        assignment = await service.assign_topic(
            AssignQuestionTopicInput(
                question_id=question.id, acting_user_id=question.author_id, topic_id=topic_id
            )
        )

        await service.unassign_topic(
            UnassignQuestionTopicInput(
                question_id=question.id,
                acting_user_id=question.author_id,
                question_topic_id=assignment.question_topic_id,
            )
        )
        assert await service.list_topics(question.id) == []

    async def test_moderator_unassigns_a_topic_from_someone_elses_question(self) -> None:
        service, questions, _, communities, topics, _ = _seeded()
        question = await _seed_question(questions, communities)
        topic_id = uuid4()
        topics.add_topic(topic_id)
        assignment = await service.assign_topic(
            AssignQuestionTopicInput(
                question_id=question.id, acting_user_id=question.author_id, topic_id=topic_id
            )
        )
        moderator_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=question.community_id,
                user_id=moderator_id,
                role=CommunityRole.MODERATOR,
            )
        )

        await service.unassign_topic(
            UnassignQuestionTopicInput(
                question_id=question.id,
                acting_user_id=moderator_id,
                question_topic_id=assignment.question_topic_id,
            )
        )
        assert await service.list_topics(question.id) == []

    async def test_unknown_assignment_raises(self) -> None:
        service, questions, _, communities, _, _ = _seeded()
        question = await _seed_question(questions, communities)

        with pytest.raises(QuestionTopicNotFoundError):
            await service.unassign_topic(
                UnassignQuestionTopicInput(
                    question_id=question.id,
                    acting_user_id=question.author_id,
                    question_topic_id=uuid4(),
                )
            )
