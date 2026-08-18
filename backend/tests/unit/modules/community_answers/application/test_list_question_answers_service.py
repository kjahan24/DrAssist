"""Unit tests for `ListQuestionAnswersService` — cursor-paginated,
pinned-first, published-only feed of one question's own answers."""

from uuid import uuid4

from app.modules.community_answers.application.dto import ListQuestionAnswersInput
from app.modules.community_answers.application.services.list_question_answers_service import (
    ListQuestionAnswersService,
)
from app.modules.community_answers.domain.entities import CommunityAnswer
from app.modules.community_answers.domain.value_objects import AnswerBody
from tests.unit.modules.community_answers.application.fakes import FakeCommunityAnswerRepository


def _make_published_answer(**overrides: object) -> CommunityAnswer:
    defaults: dict[str, object] = {
        "question_id": uuid4(),
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "topic_id": uuid4(),
        "author_id": uuid4(),
        "body": AnswerBody("Body."),
    }
    defaults.update(overrides)
    answer = CommunityAnswer.create(**defaults)  # type: ignore[arg-type]
    answer.publish()
    return answer


class TestListQuestionAnswers:
    async def test_returns_only_published_answers_for_the_question(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = ListQuestionAnswersService(answer_repository=answers)
        org_id, question_id = uuid4(), uuid4()
        published = _make_published_answer(organization_id=org_id, question_id=question_id)
        draft = CommunityAnswer.create(
            question_id=question_id,
            community_id=uuid4(),
            organization_id=org_id,
            topic_id=uuid4(),
            author_id=uuid4(),
            body=AnswerBody("Draft body."),
        )
        other_question = _make_published_answer(organization_id=org_id)
        await answers.add(published)
        await answers.add(draft)
        await answers.add(other_question)

        result = await service.list_answers(
            ListQuestionAnswersInput(organization_id=org_id, question_id=question_id)
        )
        assert [i.answer_id for i in result.items] == [published.id]

    async def test_pinned_answers_are_returned_first(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = ListQuestionAnswersService(answer_repository=answers)
        org_id, question_id = uuid4(), uuid4()
        regular = _make_published_answer(organization_id=org_id, question_id=question_id)
        pinned = _make_published_answer(organization_id=org_id, question_id=question_id)
        pinned.set_pinned(True)
        await answers.add(regular)
        await answers.add(pinned)

        result = await service.list_answers(
            ListQuestionAnswersInput(organization_id=org_id, question_id=question_id)
        )
        assert result.items[0].answer_id == pinned.id

    async def test_masks_anonymous_authors_in_the_feed(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = ListQuestionAnswersService(answer_repository=answers)
        org_id, question_id = uuid4(), uuid4()
        anonymous = _make_published_answer(
            organization_id=org_id, question_id=question_id, is_anonymous=True
        )
        await answers.add(anonymous)

        result = await service.list_answers(
            ListQuestionAnswersInput(organization_id=org_id, question_id=question_id)
        )
        assert result.items[0].author_id is None

    async def test_no_next_cursor_when_everything_fits_on_one_page(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = ListQuestionAnswersService(answer_repository=answers)
        org_id, question_id = uuid4(), uuid4()
        await answers.add(_make_published_answer(organization_id=org_id, question_id=question_id))

        result = await service.list_answers(
            ListQuestionAnswersInput(organization_id=org_id, question_id=question_id)
        )
        assert result.next_cursor is None

    async def test_returns_a_next_cursor_when_more_results_remain(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = ListQuestionAnswersService(answer_repository=answers)
        org_id, question_id = uuid4(), uuid4()
        for _ in range(3):
            await answers.add(
                _make_published_answer(organization_id=org_id, question_id=question_id)
            )

        result = await service.list_answers(
            ListQuestionAnswersInput(organization_id=org_id, question_id=question_id, limit=2)
        )
        assert len(result.items) == 2
        assert result.next_cursor is not None

    async def test_cursor_fetches_the_next_page(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = ListQuestionAnswersService(answer_repository=answers)
        org_id, question_id = uuid4(), uuid4()
        for _ in range(3):
            await answers.add(
                _make_published_answer(organization_id=org_id, question_id=question_id)
            )

        first_page = await service.list_answers(
            ListQuestionAnswersInput(organization_id=org_id, question_id=question_id, limit=2)
        )
        second_page = await service.list_answers(
            ListQuestionAnswersInput(
                organization_id=org_id,
                question_id=question_id,
                limit=2,
                cursor=first_page.next_cursor,
            )
        )
        first_ids = {i.answer_id for i in first_page.items}
        second_ids = {i.answer_id for i in second_page.items}
        assert first_ids.isdisjoint(second_ids)
