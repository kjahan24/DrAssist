"""Unit tests for `BrowseTopicQuestionsService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community_questions.application.dto import BrowseTopicQuestionsInput
from app.modules.community_questions.application.services.browse_topic_questions_service import (
    BrowseTopicQuestionsService,
)
from app.modules.community_questions.domain.entities import CommunityQuestion
from app.modules.community_questions.domain.exceptions import TopicNotFoundForQuestionError
from app.modules.community_questions.domain.value_objects import QuestionTitle
from tests.unit.modules.community_questions.application.fakes import (
    FakeCommunityQuestionRepository,
    FakeTopicQueryPort,
)


def _make_published_question(
    *, organization_id: object, primary_topic_id: object | None = None
) -> CommunityQuestion:
    question = CommunityQuestion.create(
        community_id=uuid4(),
        organization_id=organization_id,  # type: ignore[arg-type]
        author_id=uuid4(),
        primary_topic_id=primary_topic_id if primary_topic_id is not None else uuid4(),  # type: ignore[arg-type]
        title=QuestionTitle("Title"),
        body="Body",
    )
    question.publish()
    return question


class TestBrowseTopicQuestions:
    async def test_raises_when_topic_unknown(self) -> None:
        questions = FakeCommunityQuestionRepository()
        topics = FakeTopicQueryPort()
        service = BrowseTopicQuestionsService(
            question_repository=questions, topic_query_port=topics
        )

        with pytest.raises(TopicNotFoundForQuestionError):
            await service.browse(
                BrowseTopicQuestionsInput(organization_id=uuid4(), topic_id=uuid4())
            )

    async def test_returns_questions_with_the_topic_as_primary(self) -> None:
        questions = FakeCommunityQuestionRepository()
        topics = FakeTopicQueryPort()
        org_id, topic_id = uuid4(), uuid4()
        topics.add_topic(topic_id)
        matching = _make_published_question(organization_id=org_id, primary_topic_id=topic_id)
        unrelated = _make_published_question(organization_id=org_id)
        await questions.add(matching)
        await questions.add(unrelated)
        service = BrowseTopicQuestionsService(
            question_repository=questions, topic_query_port=topics
        )

        result = await service.browse(
            BrowseTopicQuestionsInput(organization_id=org_id, topic_id=topic_id)
        )
        assert [item.question_id for item in result.items] == [matching.id]

    async def test_returns_questions_with_the_topic_as_secondary(self) -> None:
        questions = FakeCommunityQuestionRepository()
        topics = FakeTopicQueryPort()
        org_id, topic_id = uuid4(), uuid4()
        topics.add_topic(topic_id)
        matching = _make_published_question(organization_id=org_id)
        questions.assign_topic_for_search(matching.id, topic_id)
        unassigned = _make_published_question(organization_id=org_id)
        await questions.add(matching)
        await questions.add(unassigned)
        service = BrowseTopicQuestionsService(
            question_repository=questions, topic_query_port=topics
        )

        result = await service.browse(
            BrowseTopicQuestionsInput(organization_id=org_id, topic_id=topic_id)
        )
        assert [item.question_id for item in result.items] == [matching.id]

    async def test_scopes_to_organization(self) -> None:
        questions = FakeCommunityQuestionRepository()
        topics = FakeTopicQueryPort()
        org_id, topic_id = uuid4(), uuid4()
        topics.add_topic(topic_id)
        matching = _make_published_question(organization_id=org_id, primary_topic_id=topic_id)
        other_org = _make_published_question(organization_id=uuid4(), primary_topic_id=topic_id)
        await questions.add(matching)
        await questions.add(other_org)
        service = BrowseTopicQuestionsService(
            question_repository=questions, topic_query_port=topics
        )

        result = await service.browse(
            BrowseTopicQuestionsInput(organization_id=org_id, topic_id=topic_id)
        )
        assert [item.question_id for item in result.items] == [matching.id]

    async def test_empty_feed_returns_no_items_and_no_cursor(self) -> None:
        questions = FakeCommunityQuestionRepository()
        topics = FakeTopicQueryPort()
        org_id, topic_id = uuid4(), uuid4()
        topics.add_topic(topic_id)
        service = BrowseTopicQuestionsService(
            question_repository=questions, topic_query_port=topics
        )

        result = await service.browse(
            BrowseTopicQuestionsInput(organization_id=org_id, topic_id=topic_id)
        )
        assert result.items == ()
        assert result.next_cursor is None
