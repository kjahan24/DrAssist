"""Unit tests for `MarkBestAnswerService`, using in-memory fakes —
covers every DOMAIN-section rule this service enforces: "Best Answer
must belong to the same Question," "Only valid published answers can
become Best Answer," "A Question can have only one Best Answer," and the
question-asker-or-moderator authorization shape."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityRole
from app.modules.community_answers.application.dto import MarkBestAnswerInput
from app.modules.community_answers.application.services.mark_best_answer_service import (
    MarkBestAnswerService,
)
from app.modules.community_answers.domain.entities import CommunityAnswer
from app.modules.community_answers.domain.events import CommunityAnswerMarkedBest
from app.modules.community_answers.domain.exceptions import (
    AnswerAlreadyBestAnswerError,
    AnswerDoesNotBelongToQuestionError,
    AnswerNotFoundError,
    AnswerNotPublishedForBestAnswerError,
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
        MarkBestAnswerService,
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
    service = MarkBestAnswerService(
        answer_repository=answers,
        community_query_port=communities,
        question_query_port=questions,
        unit_of_work=uow,
    )
    return service, answers, communities, questions, uow


async def _seed_published_answer(
    answers: FakeCommunityAnswerRepository,
    *,
    question_id: object,
    community_id: object,
    author_id: object | None = None,
) -> CommunityAnswer:
    answer = CommunityAnswer.create(
        question_id=question_id,  # type: ignore[arg-type]
        community_id=community_id,  # type: ignore[arg-type]
        organization_id=uuid4(),
        topic_id=uuid4(),
        author_id=author_id if author_id is not None else uuid4(),  # type: ignore[arg-type]
        body=AnswerBody("Body."),
    )
    answer.publish()
    answer.pull_events()
    await answers.add(answer)
    return answer


class TestMarkBestAnswer:
    async def test_question_author_can_mark_the_best_answer(self) -> None:
        service, answers, communities, questions, _ = _seeded()
        question_id, community_id, question_author_id = uuid4(), uuid4(), uuid4()
        answer = await _seed_published_answer(
            answers, question_id=question_id, community_id=community_id
        )
        questions.add_question(
            make_question_summary(
                question_id=question_id, community_id=community_id, author_id=question_author_id
            )
        )

        output = await service.execute(
            MarkBestAnswerInput(
                question_id=question_id, answer_id=answer.id, acting_user_id=question_author_id
            )
        )
        assert output.is_best_answer is True

    async def test_moderator_can_mark_the_best_answer(self) -> None:
        service, answers, communities, questions, _ = _seeded()
        question_id, community_id, moderator_id = uuid4(), uuid4(), uuid4()
        answer = await _seed_published_answer(
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

        output = await service.execute(
            MarkBestAnswerInput(
                question_id=question_id, answer_id=answer.id, acting_user_id=moderator_id
            )
        )
        assert output.is_best_answer is True

    async def test_plain_member_cannot_mark_the_best_answer(self) -> None:
        service, answers, communities, questions, _ = _seeded()
        question_id, community_id, member_id = uuid4(), uuid4(), uuid4()
        answer = await _seed_published_answer(
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
                MarkBestAnswerInput(
                    question_id=question_id, answer_id=answer.id, acting_user_id=member_id
                )
            )

    async def test_the_answers_own_author_is_not_automatically_authorized(self) -> None:
        service, answers, communities, questions, _ = _seeded()
        question_id, community_id, answer_author_id = uuid4(), uuid4(), uuid4()
        answer = await _seed_published_answer(
            answers, question_id=question_id, community_id=community_id, author_id=answer_author_id
        )
        questions.add_question(
            make_question_summary(
                question_id=question_id, community_id=community_id, author_id=uuid4()
            )
        )
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=answer_author_id)
        )

        with pytest.raises(InsufficientBestAnswerRoleError):
            await service.execute(
                MarkBestAnswerInput(
                    question_id=question_id, answer_id=answer.id, acting_user_id=answer_author_id
                )
            )

    async def test_draft_answer_cannot_become_best(self) -> None:
        answers = FakeCommunityAnswerRepository()
        communities = FakeCommunityQueryPort()
        questions = FakeQuestionQueryPort()
        service = MarkBestAnswerService(
            answer_repository=answers,
            community_query_port=communities,
            question_query_port=questions,
            unit_of_work=FakeUnitOfWork(),
        )
        question_id, community_id, question_author_id = uuid4(), uuid4(), uuid4()
        draft_answer = CommunityAnswer.create(
            question_id=question_id,
            community_id=community_id,
            organization_id=uuid4(),
            topic_id=uuid4(),
            author_id=uuid4(),
            body=AnswerBody("Body."),
        )
        await answers.add(draft_answer)
        questions.add_question(
            make_question_summary(
                question_id=question_id, community_id=community_id, author_id=question_author_id
            )
        )

        with pytest.raises(AnswerNotPublishedForBestAnswerError):
            await service.execute(
                MarkBestAnswerInput(
                    question_id=question_id,
                    answer_id=draft_answer.id,
                    acting_user_id=question_author_id,
                )
            )

    async def test_already_best_answer_raises(self) -> None:
        service, answers, communities, questions, _ = _seeded()
        question_id, community_id, question_author_id = uuid4(), uuid4(), uuid4()
        answer = await _seed_published_answer(
            answers, question_id=question_id, community_id=community_id
        )
        questions.add_question(
            make_question_summary(
                question_id=question_id, community_id=community_id, author_id=question_author_id
            )
        )
        await service.execute(
            MarkBestAnswerInput(
                question_id=question_id, answer_id=answer.id, acting_user_id=question_author_id
            )
        )

        with pytest.raises(AnswerAlreadyBestAnswerError):
            await service.execute(
                MarkBestAnswerInput(
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
        answer = await _seed_published_answer(
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
                MarkBestAnswerInput(
                    question_id=other_question_id,
                    answer_id=answer.id,
                    acting_user_id=question_author_id,
                )
            )

    async def test_unknown_answer_raises(self) -> None:
        service, _, _, _, _ = _seeded()
        with pytest.raises(AnswerNotFoundError):
            await service.execute(
                MarkBestAnswerInput(question_id=uuid4(), answer_id=uuid4(), acting_user_id=uuid4())
            )

    async def test_unknown_question_raises(self) -> None:
        service, answers, communities, questions, _ = _seeded()
        question_id, community_id = uuid4(), uuid4()
        answer = await _seed_published_answer(
            answers, question_id=question_id, community_id=community_id
        )

        with pytest.raises(QuestionNotFoundForAnswerError):
            await service.execute(
                MarkBestAnswerInput(
                    question_id=question_id, answer_id=answer.id, acting_user_id=uuid4()
                )
            )

    async def test_marking_a_new_best_answer_clears_the_previous_one(self) -> None:
        service, answers, communities, questions, _ = _seeded()
        question_id, community_id, question_author_id = uuid4(), uuid4(), uuid4()
        first = await _seed_published_answer(
            answers, question_id=question_id, community_id=community_id
        )
        second = await _seed_published_answer(
            answers, question_id=question_id, community_id=community_id
        )
        questions.add_question(
            make_question_summary(
                question_id=question_id, community_id=community_id, author_id=question_author_id
            )
        )
        await service.execute(
            MarkBestAnswerInput(
                question_id=question_id, answer_id=first.id, acting_user_id=question_author_id
            )
        )

        await service.execute(
            MarkBestAnswerInput(
                question_id=question_id, answer_id=second.id, acting_user_id=question_author_id
            )
        )

        stored_first = await answers.get_by_id(first.id)
        stored_second = await answers.get_by_id(second.id)
        assert stored_first is not None and stored_first.is_best_answer is False
        assert stored_second is not None and stored_second.is_best_answer is True

    async def test_commits_the_unit_of_work(self) -> None:
        service, answers, communities, questions, uow = _seeded()
        question_id, community_id, question_author_id = uuid4(), uuid4(), uuid4()
        answer = await _seed_published_answer(
            answers, question_id=question_id, community_id=community_id
        )
        questions.add_question(
            make_question_summary(
                question_id=question_id, community_id=community_id, author_id=question_author_id
            )
        )

        await service.execute(
            MarkBestAnswerInput(
                question_id=question_id, answer_id=answer.id, acting_user_id=question_author_id
            )
        )
        assert uow.committed is True

    async def test_publishes_a_community_answer_marked_best_event(self) -> None:
        service, answers, communities, questions, uow = _seeded()
        question_id, community_id, question_author_id = uuid4(), uuid4(), uuid4()
        answer = await _seed_published_answer(
            answers, question_id=question_id, community_id=community_id
        )
        questions.add_question(
            make_question_summary(
                question_id=question_id, community_id=community_id, author_id=question_author_id
            )
        )

        await service.execute(
            MarkBestAnswerInput(
                question_id=question_id, answer_id=answer.id, acting_user_id=question_author_id
            )
        )
        assert any(isinstance(e, CommunityAnswerMarkedBest) for e in uow.published_events)
