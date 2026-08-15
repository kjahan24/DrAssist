"""Unit tests for `SearchQuestionsService`, using in-memory fakes."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.modules.community_questions.application.dto import SearchQuestionsInput
from app.modules.community_questions.application.services.search_questions_service import (
    SearchQuestionsService,
)
from app.modules.community_questions.domain.entities import CommunityQuestion
from app.modules.community_questions.domain.enums import (
    QuestionStatus,
    QuestionType,
    QuestionVisibility,
)
from app.modules.community_questions.domain.value_objects import QuestionTitle
from tests.unit.modules.community_questions.application.fakes import FakeCommunityQuestionRepository


def _make_question(**overrides: object) -> CommunityQuestion:
    defaults: dict[str, object] = {
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "author_id": uuid4(),
        "primary_topic_id": uuid4(),
        "title": QuestionTitle("Title"),
        "body": "Body",
    }
    defaults.update(overrides)
    return CommunityQuestion.create(**defaults)  # type: ignore[arg-type]


class TestSearchQuestions:
    async def test_matches_a_keyword_in_the_title(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = SearchQuestionsService(question_repository=questions)
        org_id = uuid4()
        matching = _make_question(organization_id=org_id, title=QuestionTitle("Managing Diabetes"))
        other = _make_question(organization_id=org_id, title=QuestionTitle("Unrelated Topic"))
        await questions.add(matching)
        await questions.add(other)

        result = await service.search(
            SearchQuestionsInput(organization_id=org_id, query="diabetes")
        )
        assert result.total == 1
        assert result.items[0].question_id == matching.id

    async def test_scopes_to_organization(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = SearchQuestionsService(question_repository=questions)
        org_id = uuid4()
        matching = _make_question(organization_id=org_id, title=QuestionTitle("Shared Term"))
        other_org = _make_question(title=QuestionTitle("Shared Term"))
        await questions.add(matching)
        await questions.add(other_org)

        result = await service.search(SearchQuestionsInput(organization_id=org_id, query="Shared"))
        assert result.total == 1
        assert result.items[0].question_id == matching.id

    async def test_no_match_returns_empty(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = SearchQuestionsService(question_repository=questions)
        org_id = uuid4()
        await questions.add(
            _make_question(organization_id=org_id, title=QuestionTitle("Something Else"))
        )

        result = await service.search(
            SearchQuestionsInput(organization_id=org_id, query="zzz-no-match")
        )
        assert result.total == 0
        assert result.items == ()

    async def test_filters_by_community(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = SearchQuestionsService(question_repository=questions)
        org_id, community_id = uuid4(), uuid4()
        matching = _make_question(organization_id=org_id, community_id=community_id)
        other = _make_question(organization_id=org_id)
        await questions.add(matching)
        await questions.add(other)

        result = await service.search(
            SearchQuestionsInput(organization_id=org_id, query="", community_id=community_id)
        )
        assert [i.question_id for i in result.items] == [matching.id]

    async def test_filters_by_author(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = SearchQuestionsService(question_repository=questions)
        org_id, author_id = uuid4(), uuid4()
        matching = _make_question(organization_id=org_id, author_id=author_id)
        other = _make_question(organization_id=org_id)
        await questions.add(matching)
        await questions.add(other)

        result = await service.search(
            SearchQuestionsInput(organization_id=org_id, query="", author_id=author_id)
        )
        assert [i.question_id for i in result.items] == [matching.id]

    async def test_filters_by_question_type(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = SearchQuestionsService(question_repository=questions)
        org_id = uuid4()
        matching = _make_question(
            organization_id=org_id, question_type=QuestionType.RESEARCH_QUESTION
        )
        other = _make_question(organization_id=org_id, question_type=QuestionType.GENERAL)
        await questions.add(matching)
        await questions.add(other)

        result = await service.search(
            SearchQuestionsInput(
                organization_id=org_id, query="", question_type=(QuestionType.RESEARCH_QUESTION,)
            )
        )
        assert [i.question_id for i in result.items] == [matching.id]

    async def test_filters_by_status(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = SearchQuestionsService(question_repository=questions)
        org_id = uuid4()
        published = _make_question(organization_id=org_id)
        published.publish()
        draft = _make_question(organization_id=org_id)
        await questions.add(published)
        await questions.add(draft)

        result = await service.search(
            SearchQuestionsInput(
                organization_id=org_id, query="", status=(QuestionStatus.PUBLISHED,)
            )
        )
        assert [i.question_id for i in result.items] == [published.id]

    async def test_filters_by_visibility(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = SearchQuestionsService(question_repository=questions)
        org_id = uuid4()
        matching = _make_question(organization_id=org_id, visibility=QuestionVisibility.PRIVATE)
        other = _make_question(organization_id=org_id, visibility=QuestionVisibility.PUBLIC)
        await questions.add(matching)
        await questions.add(other)

        result = await service.search(
            SearchQuestionsInput(
                organization_id=org_id, query="", visibility=(QuestionVisibility.PRIVATE,)
            )
        )
        assert [i.question_id for i in result.items] == [matching.id]

    async def test_filters_pinned_only(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = SearchQuestionsService(question_repository=questions)
        org_id = uuid4()
        pinned = _make_question(organization_id=org_id)
        pinned.set_pinned(True)
        other = _make_question(organization_id=org_id)
        await questions.add(pinned)
        await questions.add(other)

        result = await service.search(
            SearchQuestionsInput(organization_id=org_id, query="", pinned_only=True)
        )
        assert [i.question_id for i in result.items] == [pinned.id]

    async def test_filters_featured_only(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = SearchQuestionsService(question_repository=questions)
        org_id = uuid4()
        featured = _make_question(organization_id=org_id)
        featured.set_featured(True)
        other = _make_question(organization_id=org_id)
        await questions.add(featured)
        await questions.add(other)

        result = await service.search(
            SearchQuestionsInput(organization_id=org_id, query="", featured_only=True)
        )
        assert [i.question_id for i in result.items] == [featured.id]

    async def test_respects_limit_and_offset(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = SearchQuestionsService(question_repository=questions)
        org_id = uuid4()
        for _ in range(3):
            await questions.add(_make_question(organization_id=org_id))

        first_page = await service.search(
            SearchQuestionsInput(organization_id=org_id, query="", limit=2, offset=0)
        )
        second_page = await service.search(
            SearchQuestionsInput(organization_id=org_id, query="", limit=2, offset=2)
        )
        assert first_page.total == 3
        assert len(first_page.items) == 2
        assert len(second_page.items) == 1

    async def test_filters_by_created_date_range(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = SearchQuestionsService(question_repository=questions)
        org_id = uuid4()
        question = _make_question(organization_id=org_id)
        await questions.add(question)
        now = datetime.now(UTC)

        in_range = await service.search(
            SearchQuestionsInput(
                organization_id=org_id,
                query="",
                created_from=now - timedelta(days=1),
                created_to=now + timedelta(days=1),
            )
        )
        out_of_range = await service.search(
            SearchQuestionsInput(
                organization_id=org_id, query="", created_from=now + timedelta(days=1)
            )
        )
        assert [i.question_id for i in in_range.items] == [question.id]
        assert out_of_range.items == ()
