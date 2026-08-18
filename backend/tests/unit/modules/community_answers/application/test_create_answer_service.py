"""Unit tests for `CreateAnswerService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community_answers.application.dto import CreateAnswerInput
from app.modules.community_answers.application.services.create_answer_service import (
    CreateAnswerService,
)
from app.modules.community_answers.domain.enums import AnswerStatus, AnswerVisibility
from app.modules.community_answers.domain.events import CommunityAnswerCreated
from app.modules.community_answers.domain.exceptions import (
    AnswerMembershipRequiredError,
    QuestionNotAcceptingAnswersError,
    QuestionNotFoundForAnswerError,
    QuestionNotViewableForAnswerError,
)
from app.modules.community_questions.public.dto import QuestionStatus, QuestionVisibility
from tests.unit.modules.community_answers.application.fakes import (
    FakeCommunityAnswerRepository,
    FakeCommunityQueryPort,
    FakeQuestionQueryPort,
    FakeUnitOfWork,
    make_member_summary,
    make_question_summary,
)


def _seeded() -> (
    tuple[
        CreateAnswerService,
        FakeCommunityAnswerRepository,
        FakeCommunityQueryPort,
        FakeQuestionQueryPort,
        FakeUnitOfWork,
    ]
):
    answers = FakeCommunityAnswerRepository()
    communities = FakeCommunityQueryPort()
    questions = FakeQuestionQueryPort()
    uow = FakeUnitOfWork()
    service = CreateAnswerService(
        answer_repository=answers,
        community_query_port=communities,
        question_query_port=questions,
        unit_of_work=uow,
    )
    return service, answers, communities, questions, uow


def _seed_membership(
    communities: FakeCommunityQueryPort, *, community_id: object, user_id: object
) -> None:
    communities.add_membership(make_member_summary(community_id=community_id, user_id=user_id))


class TestCreateAnswer:
    async def test_creates_an_answer(self) -> None:
        service, answers, communities, questions, _ = _seeded()
        community_id, author_id, question_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        questions.add_question(
            make_question_summary(
                question_id=question_id, community_id=community_id, status=QuestionStatus.PUBLISHED
            )
        )

        output = await service.execute(
            CreateAnswerInput(question_id=question_id, author_id=author_id, body="An answer body.")
        )
        stored = await answers.get_by_id(output.answer_id)
        assert stored is not None
        assert str(stored.body) == "An answer body."
        assert stored.question_id == question_id
        assert stored.author_id == author_id

    async def test_new_answer_defaults_to_draft_status(self) -> None:
        service, _, communities, questions, _ = _seeded()
        community_id, author_id, question_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        questions.add_question(
            make_question_summary(question_id=question_id, community_id=community_id)
        )

        output = await service.execute(
            CreateAnswerInput(question_id=question_id, author_id=author_id, body="Body.")
        )
        assert output.status is AnswerStatus.DRAFT

    async def test_denormalizes_community_organization_and_topic_from_the_question(self) -> None:
        service, answers, communities, questions, _ = _seeded()
        community_id, author_id, question_id = uuid4(), uuid4(), uuid4()
        organization_id, topic_id = uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        questions.add_question(
            make_question_summary(
                question_id=question_id,
                community_id=community_id,
                organization_id=organization_id,
                primary_topic_id=topic_id,
            )
        )

        output = await service.execute(
            CreateAnswerInput(question_id=question_id, author_id=author_id, body="Body.")
        )
        stored = await answers.get_by_id(output.answer_id)
        assert stored is not None
        assert stored.community_id == community_id
        assert stored.organization_id == organization_id
        assert stored.topic_id == topic_id

    async def test_accepts_an_explicit_summary(self) -> None:
        service, answers, communities, questions, _ = _seeded()
        community_id, author_id, question_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        questions.add_question(
            make_question_summary(question_id=question_id, community_id=community_id)
        )

        output = await service.execute(
            CreateAnswerInput(
                question_id=question_id,
                author_id=author_id,
                body="Body.",
                summary="A hand-written summary.",
            )
        )
        stored = await answers.get_by_id(output.answer_id)
        assert stored is not None
        assert str(stored.summary) == "A hand-written summary."

    async def test_accepts_explicit_visibility(self) -> None:
        service, answers, communities, questions, _ = _seeded()
        community_id, author_id, question_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        questions.add_question(
            make_question_summary(question_id=question_id, community_id=community_id)
        )

        output = await service.execute(
            CreateAnswerInput(
                question_id=question_id,
                author_id=author_id,
                body="Body.",
                visibility=AnswerVisibility.PRIVATE,
            )
        )
        stored = await answers.get_by_id(output.answer_id)
        assert stored is not None
        assert stored.visibility is AnswerVisibility.PRIVATE

    async def test_accepts_is_anonymous(self) -> None:
        service, answers, communities, questions, _ = _seeded()
        community_id, author_id, question_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        questions.add_question(
            make_question_summary(question_id=question_id, community_id=community_id)
        )

        output = await service.execute(
            CreateAnswerInput(
                question_id=question_id, author_id=author_id, body="Body.", is_anonymous=True
            )
        )
        stored = await answers.get_by_id(output.answer_id)
        assert stored is not None
        assert stored.is_anonymous is True

    async def test_unknown_question_raises(self) -> None:
        service, _, communities, _, _ = _seeded()
        community_id, author_id = uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)

        with pytest.raises(QuestionNotFoundForAnswerError):
            await service.execute(
                CreateAnswerInput(question_id=uuid4(), author_id=author_id, body="Body.")
            )

    async def test_draft_question_rejects_new_answers(self) -> None:
        service, _, communities, questions, _ = _seeded()
        community_id, author_id, question_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        questions.add_question(
            make_question_summary(
                question_id=question_id, community_id=community_id, status=QuestionStatus.DRAFT
            )
        )

        with pytest.raises(QuestionNotAcceptingAnswersError):
            await service.execute(
                CreateAnswerInput(question_id=question_id, author_id=author_id, body="Body.")
            )

    async def test_closed_or_archived_question_rejects_new_answers(self) -> None:
        service, _, communities, questions, _ = _seeded()
        community_id, author_id, question_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        questions.add_question(
            make_question_summary(
                question_id=question_id, community_id=community_id, status=QuestionStatus.ARCHIVED
            )
        )

        with pytest.raises(QuestionNotAcceptingAnswersError):
            await service.execute(
                CreateAnswerInput(question_id=question_id, author_id=author_id, body="Body.")
            )

    async def test_non_member_raises(self) -> None:
        service, _, _, questions, _ = _seeded()
        community_id, question_id = uuid4(), uuid4()
        questions.add_question(
            make_question_summary(question_id=question_id, community_id=community_id)
        )

        with pytest.raises(AnswerMembershipRequiredError):
            await service.execute(
                CreateAnswerInput(question_id=question_id, author_id=uuid4(), body="Body.")
            )

    async def test_private_question_not_authored_by_caller_rejects_the_answer(self) -> None:
        service, _, communities, questions, _ = _seeded()
        community_id, author_id, question_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        questions.add_question(
            make_question_summary(
                question_id=question_id,
                community_id=community_id,
                visibility=QuestionVisibility.PRIVATE,
                author_id=uuid4(),
            )
        )

        with pytest.raises(QuestionNotViewableForAnswerError):
            await service.execute(
                CreateAnswerInput(question_id=question_id, author_id=author_id, body="Body.")
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, communities, questions, uow = _seeded()
        community_id, author_id, question_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        questions.add_question(
            make_question_summary(question_id=question_id, community_id=community_id)
        )

        await service.execute(
            CreateAnswerInput(question_id=question_id, author_id=author_id, body="Body.")
        )
        assert uow.committed is True

    async def test_publishes_a_community_answer_created_event(self) -> None:
        service, _, communities, questions, uow = _seeded()
        community_id, author_id, question_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        questions.add_question(
            make_question_summary(question_id=question_id, community_id=community_id)
        )

        await service.execute(
            CreateAnswerInput(question_id=question_id, author_id=author_id, body="Body.")
        )
        assert any(isinstance(e, CommunityAnswerCreated) for e in uow.published_events)
