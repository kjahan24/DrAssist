"""Unit tests for `RemoveBestAnswerService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityRole
from app.modules.community_answers.application.dto import RemoveBestAnswerInput
from app.modules.community_answers.application.services.remove_best_answer_service import (
    RemoveBestAnswerService,
)
from app.modules.community_answers.domain.entities import CommunityAnswer
from app.modules.community_answers.domain.exceptions import (
    AnswerDoesNotBelongToQuestionError,
    AnswerNotBestAnswerError,
    AnswerNotFoundError,
    InsufficientBestAnswerRoleError,
    QuestionNotFoundForAnswerError,
)
from app.modules.community_answers.domain.value_objects import AnswerBody
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
        RemoveBestAnswerService,
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
    service = RemoveBestAnswerService(
        answer_repository=answers,
        community_query_port=communities,
        question_query_port=questions,
        unit_of_work=uow,
    )
    return service, answers, communities, questions, uow


async def _seed_best_answer(
    answers: FakeCommunityAnswerRepository, *, question_id: object, community_id: object
) -> CommunityAnswer:
    answer = CommunityAnswer.create(
        question_id=question_id,  # type: ignore[arg-type]
        community_id=community_id,  # type: ignore[arg-type]
        organization_id=uuid4(),
        topic_id=uuid4(),
        author_id=uuid4(),
        body=AnswerBody("Body."),
    )
    answer.publish()
    answer.mark_as_best()
    answer.pull_events()
    await answers.add(answer)
    return answer


class TestRemoveBestAnswer:
    async def test_question_author_can_clear_the_best_answer(self) -> None:
        service, answers, communities, questions, _ = _seeded()
        question_id, community_id, question_author_id = uuid4(), uuid4(), uuid4()
        answer = await _seed_best_answer(
            answers, question_id=question_id, community_id=community_id
        )
        questions.add_question(
            make_question_summary(
                question_id=question_id, community_id=community_id, author_id=question_author_id
            )
        )

        await service.execute(
            RemoveBestAnswerInput(
                question_id=question_id, answer_id=answer.id, acting_user_id=question_author_id
            )
        )
        stored = await answers.get_by_id(answer.id)
        assert stored is not None
        assert stored.is_best_answer is False

    async def test_moderator_can_clear_the_best_answer(self) -> None:
        service, answers, communities, questions, _ = _seeded()
        question_id, community_id, moderator_id = uuid4(), uuid4(), uuid4()
        answer = await _seed_best_answer(
            answers, question_id=question_id, community_id=community_id
        )
        questions.add_question(
            make_question_summary(question_id=question_id, community_id=community_id)
        )
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )

        await service.execute(
            RemoveBestAnswerInput(
                question_id=question_id, answer_id=answer.id, acting_user_id=moderator_id
            )
        )
        stored = await answers.get_by_id(answer.id)
        assert stored is not None
        assert stored.is_best_answer is False

    async def test_plain_member_cannot_clear_the_best_answer(self) -> None:
        service, answers, communities, questions, _ = _seeded()
        question_id, community_id, member_id = uuid4(), uuid4(), uuid4()
        answer = await _seed_best_answer(
            answers, question_id=question_id, community_id=community_id
        )
        questions.add_question(
            make_question_summary(question_id=question_id, community_id=community_id)
        )
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=member_id)
        )

        with pytest.raises(InsufficientBestAnswerRoleError):
            await service.execute(
                RemoveBestAnswerInput(
                    question_id=question_id, answer_id=answer.id, acting_user_id=member_id
                )
            )

    async def test_removing_best_when_not_currently_best_raises(self) -> None:
        service, answers, communities, questions, _ = _seeded()
        question_id, community_id, question_author_id = uuid4(), uuid4(), uuid4()
        answer = CommunityAnswer.create(
            question_id=question_id,
            community_id=community_id,
            organization_id=uuid4(),
            topic_id=uuid4(),
            author_id=uuid4(),
            body=AnswerBody("Body."),
        )
        answer.publish()
        await answers.add(answer)
        questions.add_question(
            make_question_summary(
                question_id=question_id, community_id=community_id, author_id=question_author_id
            )
        )

        with pytest.raises(AnswerNotBestAnswerError):
            await service.execute(
                RemoveBestAnswerInput(
                    question_id=question_id, answer_id=answer.id, acting_user_id=question_author_id
                )
            )

    async def test_answer_belonging_to_a_different_question_raises(self) -> None:
        service, answers, communities, questions, _ = _seeded()
        question_id, other_question_id, community_id, question_author_id = (
            uuid4(),
            uuid4(),
            uuid4(),
            uuid4(),
        )
        answer = await _seed_best_answer(
            answers, question_id=question_id, community_id=community_id
        )
        questions.add_question(
            make_question_summary(
                question_id=other_question_id,
                community_id=community_id,
                author_id=question_author_id,
            )
        )

        with pytest.raises(AnswerDoesNotBelongToQuestionError):
            await service.execute(
                RemoveBestAnswerInput(
                    question_id=other_question_id,
                    answer_id=answer.id,
                    acting_user_id=question_author_id,
                )
            )

    async def test_unknown_answer_raises(self) -> None:
        service, _, _, _, _ = _seeded()
        with pytest.raises(AnswerNotFoundError):
            await service.execute(
                RemoveBestAnswerInput(
                    question_id=uuid4(), answer_id=uuid4(), acting_user_id=uuid4()
                )
            )

    async def test_unknown_question_raises(self) -> None:
        service, answers, communities, questions, _ = _seeded()
        question_id, community_id = uuid4(), uuid4()
        answer = await _seed_best_answer(
            answers, question_id=question_id, community_id=community_id
        )

        with pytest.raises(QuestionNotFoundForAnswerError):
            await service.execute(
                RemoveBestAnswerInput(
                    question_id=question_id, answer_id=answer.id, acting_user_id=uuid4()
                )
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, answers, communities, questions, uow = _seeded()
        question_id, community_id, question_author_id = uuid4(), uuid4(), uuid4()
        answer = await _seed_best_answer(
            answers, question_id=question_id, community_id=community_id
        )
        questions.add_question(
            make_question_summary(
                question_id=question_id, community_id=community_id, author_id=question_author_id
            )
        )

        await service.execute(
            RemoveBestAnswerInput(
                question_id=question_id, answer_id=answer.id, acting_user_id=question_author_id
            )
        )
        assert uow.committed is True
