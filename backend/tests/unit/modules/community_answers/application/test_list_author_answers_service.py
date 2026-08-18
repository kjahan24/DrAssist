"""Unit tests for `ListAuthorAnswersService` — cursor-paginated,
published-only feed of one author's own answers across every question."""

from uuid import uuid4

from app.modules.community_answers.application.dto import ListAuthorAnswersInput
from app.modules.community_answers.application.services.list_author_answers_service import (
    ListAuthorAnswersService,
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


class TestListAuthorAnswers:
    async def test_returns_only_the_authors_own_published_answers(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = ListAuthorAnswersService(answer_repository=answers)
        org_id, author_id = uuid4(), uuid4()
        mine = _make_published_answer(organization_id=org_id, author_id=author_id)
        draft = CommunityAnswer.create(
            question_id=uuid4(),
            community_id=uuid4(),
            organization_id=org_id,
            topic_id=uuid4(),
            author_id=author_id,
            body=AnswerBody("Draft."),
        )
        someone_elses = _make_published_answer(organization_id=org_id)
        await answers.add(mine)
        await answers.add(draft)
        await answers.add(someone_elses)

        result = await service.list_answers(
            ListAuthorAnswersInput(organization_id=org_id, author_id=author_id)
        )
        assert [i.answer_id for i in result.items] == [mine.id]

    async def test_masks_author_id_when_the_answer_itself_is_anonymous(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = ListAuthorAnswersService(answer_repository=answers)
        org_id, author_id = uuid4(), uuid4()
        anonymous = _make_published_answer(
            organization_id=org_id, author_id=author_id, is_anonymous=True
        )
        await answers.add(anonymous)

        result = await service.list_answers(
            ListAuthorAnswersInput(organization_id=org_id, author_id=author_id)
        )
        assert result.items[0].author_id is None

    async def test_returns_a_next_cursor_when_more_results_remain(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = ListAuthorAnswersService(answer_repository=answers)
        org_id, author_id = uuid4(), uuid4()
        for _ in range(3):
            await answers.add(_make_published_answer(organization_id=org_id, author_id=author_id))

        result = await service.list_answers(
            ListAuthorAnswersInput(organization_id=org_id, author_id=author_id, limit=2)
        )
        assert len(result.items) == 2
        assert result.next_cursor is not None
