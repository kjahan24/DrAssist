"""Unit tests for `PublishQuestionService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityRole
from app.modules.community_questions.application.dto import PublishQuestionInput
from app.modules.community_questions.application.services.publish_question_service import (
    PublishQuestionService,
)
from app.modules.community_questions.domain.entities import CommunityQuestion
from app.modules.community_questions.domain.enums import QuestionStatus
from app.modules.community_questions.domain.events import CommunityQuestionPublished
from app.modules.community_questions.domain.exceptions import (
    InsufficientQuestionRoleError,
    QuestionAlreadyPublishedError,
    QuestionNotFoundError,
)
from app.modules.community_questions.domain.value_objects import QuestionTitle
from tests.unit.modules.community_questions.application.fakes import (
    FakeCommunityQueryPort,
    FakeCommunityQuestionRepository,
    FakeUnitOfWork,
    make_community_summary,
    make_member_summary,
)


def _seeded() -> (
    tuple[
        PublishQuestionService,
        FakeCommunityQuestionRepository,
        FakeCommunityQueryPort,
        FakeUnitOfWork,
    ]
):
    questions = FakeCommunityQuestionRepository()
    communities = FakeCommunityQueryPort()
    uow = FakeUnitOfWork()
    service = PublishQuestionService(
        question_repository=questions, community_query_port=communities, unit_of_work=uow
    )
    return service, questions, communities, uow


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


class TestPublishQuestion:
    async def test_author_publishes_the_question(self) -> None:
        service, questions, communities, _ = _seeded()
        question = await _seed_question(questions, communities)

        await service.execute(
            PublishQuestionInput(question_id=question.id, acting_user_id=question.author_id)
        )

        stored = await questions.get_by_id(question.id)
        assert stored is not None
        assert stored.status is QuestionStatus.PUBLISHED
        assert stored.published_at is not None

    async def test_moderator_can_publish_someone_elses_question(self) -> None:
        service, questions, communities, _ = _seeded()
        question = await _seed_question(questions, communities)
        moderator_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=question.community_id,
                user_id=moderator_id,
                role=CommunityRole.MODERATOR,
            )
        )

        await service.execute(
            PublishQuestionInput(question_id=question.id, acting_user_id=moderator_id)
        )
        stored = await questions.get_by_id(question.id)
        assert stored is not None
        assert stored.status is QuestionStatus.PUBLISHED

    async def test_plain_member_cannot_publish_someone_elses_question(self) -> None:
        service, questions, communities, _ = _seeded()
        question = await _seed_question(questions, communities)
        member_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=question.community_id, user_id=member_id, role=CommunityRole.MEMBER
            )
        )

        with pytest.raises(InsufficientQuestionRoleError):
            await service.execute(
                PublishQuestionInput(question_id=question.id, acting_user_id=member_id)
            )

    async def test_unknown_question_raises(self) -> None:
        service, _, _, _ = _seeded()
        with pytest.raises(QuestionNotFoundError):
            await service.execute(PublishQuestionInput(question_id=uuid4(), acting_user_id=uuid4()))

    async def test_already_published_raises(self) -> None:
        service, questions, communities, _ = _seeded()
        question = await _seed_question(questions, communities)
        await service.execute(
            PublishQuestionInput(question_id=question.id, acting_user_id=question.author_id)
        )

        with pytest.raises(QuestionAlreadyPublishedError):
            await service.execute(
                PublishQuestionInput(question_id=question.id, acting_user_id=question.author_id)
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, questions, communities, uow = _seeded()
        question = await _seed_question(questions, communities)
        await service.execute(
            PublishQuestionInput(question_id=question.id, acting_user_id=question.author_id)
        )
        assert uow.committed is True

    async def test_publishes_a_community_question_published_event(self) -> None:
        service, questions, communities, uow = _seeded()
        question = await _seed_question(questions, communities)
        await service.execute(
            PublishQuestionInput(question_id=question.id, acting_user_id=question.author_id)
        )
        assert any(isinstance(e, CommunityQuestionPublished) for e in uow.published_events)

    async def test_returns_a_summary_with_published_status(self) -> None:
        service, questions, communities, _ = _seeded()
        question = await _seed_question(questions, communities)
        summary = await service.execute(
            PublishQuestionInput(question_id=question.id, acting_user_id=question.author_id)
        )
        assert summary.status is QuestionStatus.PUBLISHED
