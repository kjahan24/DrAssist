"""Unit tests for `SearchAnswersService`, using in-memory fakes."""

from uuid import uuid4

from app.modules.community_answers.application.dto import SearchAnswersInput
from app.modules.community_answers.application.services.search_answers_service import (
    SearchAnswersService,
)
from app.modules.community_answers.domain.entities import CommunityAnswer
from app.modules.community_answers.domain.value_objects import AnswerBody, AnswerSummary
from tests.unit.modules.community_answers.application.fakes import FakeCommunityAnswerRepository


def _make_answer(**overrides: object) -> CommunityAnswer:
    defaults: dict[str, object] = {
        "question_id": uuid4(),
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "topic_id": uuid4(),
        "author_id": uuid4(),
        "body": AnswerBody("Body."),
    }
    defaults.update(overrides)
    return CommunityAnswer.create(**defaults)  # type: ignore[arg-type]


class TestSearchAnswers:
    async def test_finds_a_match_in_the_body(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = SearchAnswersService(answer_repository=answers)
        org_id = uuid4()
        matching = _make_answer(
            organization_id=org_id, body=AnswerBody("Hypertension management tips.")
        )
        other = _make_answer(organization_id=org_id, body=AnswerBody("Something unrelated."))
        await answers.add(matching)
        await answers.add(other)

        result = await service.search(
            SearchAnswersInput(organization_id=org_id, query="hypertension")
        )
        assert [i.answer_id for i in result.items] == [matching.id]

    async def test_scoped_to_organization(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = SearchAnswersService(answer_repository=answers)
        org_id = uuid4()
        matching = _make_answer(organization_id=org_id, body=AnswerBody("Shared keyword text."))
        other_org = _make_answer(body=AnswerBody("Shared keyword text."))
        await answers.add(matching)
        await answers.add(other_org)

        result = await service.search(SearchAnswersInput(organization_id=org_id, query="keyword"))
        assert [i.answer_id for i in result.items] == [matching.id]

    async def test_filters_by_question_in_addition_to_the_keyword(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = SearchAnswersService(answer_repository=answers)
        org_id, question_id = uuid4(), uuid4()
        matching = _make_answer(
            organization_id=org_id, question_id=question_id, body=AnswerBody("Keyword here.")
        )
        other_question = _make_answer(organization_id=org_id, body=AnswerBody("Keyword here."))
        await answers.add(matching)
        await answers.add(other_question)

        result = await service.search(
            SearchAnswersInput(organization_id=org_id, query="keyword", question_id=question_id)
        )
        assert [i.answer_id for i in result.items] == [matching.id]

    async def test_no_matches_returns_empty(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = SearchAnswersService(answer_repository=answers)
        org_id = uuid4()
        await answers.add(
            _make_answer(organization_id=org_id, body=AnswerBody("Unrelated content."))
        )

        result = await service.search(SearchAnswersInput(organization_id=org_id, query="nomatch"))
        assert result.items == ()
        assert result.total == 0

    async def test_respects_limit_and_offset(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = SearchAnswersService(answer_repository=answers)
        org_id = uuid4()
        for _ in range(3):
            await answers.add(_make_answer(organization_id=org_id, body=AnswerBody("Shared term.")))

        result = await service.search(
            SearchAnswersInput(organization_id=org_id, query="shared", limit=2, offset=1)
        )
        assert result.total == 3
        assert len(result.items) == 2

    async def test_finds_a_match_only_present_in_the_summary(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = SearchAnswersService(answer_repository=answers)
        org_id = uuid4()
        matching = _make_answer(
            organization_id=org_id,
            body=AnswerBody("Generic clinical guidance."),
            summary=AnswerSummary("Hand-written note mentioning oncology specifically."),
        )
        await answers.add(matching)

        result = await service.search(SearchAnswersInput(organization_id=org_id, query="oncology"))
        assert [i.answer_id for i in result.items] == [matching.id]

    async def test_combines_best_answer_and_featured_filters_with_the_keyword(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = SearchAnswersService(answer_repository=answers)
        org_id = uuid4()
        best_and_featured = _make_answer(organization_id=org_id, body=AnswerBody("Keyword text."))
        best_and_featured.publish()
        best_and_featured.mark_as_best()
        best_and_featured.set_featured(True)
        best_only = _make_answer(organization_id=org_id, body=AnswerBody("Keyword text."))
        best_only.publish()
        best_only.mark_as_best()
        await answers.add(best_and_featured)
        await answers.add(best_only)

        result = await service.search(
            SearchAnswersInput(
                organization_id=org_id, query="keyword", best_answer_only=True, featured_only=True
            )
        )
        assert [i.answer_id for i in result.items] == [best_and_featured.id]
