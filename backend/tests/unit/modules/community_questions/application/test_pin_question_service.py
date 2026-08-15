"""Unit tests for `PinQuestionService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityRole
from app.modules.community_questions.application.dto import SetQuestionPinnedInput
from app.modules.community_questions.application.services.pin_question_service import (
    PinQuestionService,
)
from app.modules.community_questions.domain.entities import CommunityQuestion
from app.modules.community_questions.domain.events import CommunityQuestionPinnedChanged
from app.modules.community_questions.domain.exceptions import (
    InsufficientQuestionRoleError,
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
        PinQuestionService, FakeCommunityQuestionRepository, FakeCommunityQueryPort, FakeUnitOfWork
    ]
):
    questions = FakeCommunityQuestionRepository()
    communities = FakeCommunityQueryPort()
    uow = FakeUnitOfWork()
    service = PinQuestionService(
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


class TestPinQuestion:
    async def test_moderator_pins_the_question(self) -> None:
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
            SetQuestionPinnedInput(
                question_id=question.id, acting_user_id=moderator_id, pinned=True
            )
        )
        stored = await questions.get_by_id(question.id)
        assert stored is not None
        assert stored.is_pinned is True

    async def test_author_cannot_pin_their_own_question(self) -> None:
        service, questions, communities, _ = _seeded()
        question = await _seed_question(questions, communities)
        communities.add_membership(
            make_member_summary(
                community_id=question.community_id,
                user_id=question.author_id,
                role=CommunityRole.MEMBER,
            )
        )

        with pytest.raises(InsufficientQuestionRoleError):
            await service.execute(
                SetQuestionPinnedInput(
                    question_id=question.id, acting_user_id=question.author_id, pinned=True
                )
            )

    async def test_unknown_question_raises(self) -> None:
        service, _, _, _ = _seeded()
        with pytest.raises(QuestionNotFoundError):
            await service.execute(
                SetQuestionPinnedInput(question_id=uuid4(), acting_user_id=uuid4(), pinned=True)
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, questions, communities, uow = _seeded()
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
            SetQuestionPinnedInput(
                question_id=question.id, acting_user_id=moderator_id, pinned=True
            )
        )
        assert uow.committed is True

    async def test_publishes_a_community_question_pinned_changed_event(self) -> None:
        service, questions, communities, uow = _seeded()
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
            SetQuestionPinnedInput(
                question_id=question.id, acting_user_id=moderator_id, pinned=True
            )
        )
        assert any(isinstance(e, CommunityQuestionPinnedChanged) for e in uow.published_events)
