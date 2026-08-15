"""Unit tests for `BrowseAuthorQuestionsService`, using in-memory fakes."""

from uuid import uuid4

from app.modules.community_questions.application.dto import BrowseAuthorQuestionsInput
from app.modules.community_questions.application.services.browse_author_questions_service import (
    BrowseAuthorQuestionsService,
)
from app.modules.community_questions.domain.entities import CommunityQuestion
from app.modules.community_questions.domain.value_objects import QuestionTitle
from tests.unit.modules.community_questions.application.fakes import FakeCommunityQuestionRepository


def _make_published_question(*, organization_id: object, author_id: object) -> CommunityQuestion:
    question = CommunityQuestion.create(
        community_id=uuid4(),
        organization_id=organization_id,  # type: ignore[arg-type]
        author_id=author_id,  # type: ignore[arg-type]
        primary_topic_id=uuid4(),
        title=QuestionTitle("Title"),
        body="Body",
    )
    question.publish()
    return question


class TestBrowseAuthorQuestions:
    async def test_returns_only_the_given_authors_questions(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = BrowseAuthorQuestionsService(question_repository=questions)
        org_id, author_id = uuid4(), uuid4()
        matching = _make_published_question(organization_id=org_id, author_id=author_id)
        other_author = _make_published_question(organization_id=org_id, author_id=uuid4())
        await questions.add(matching)
        await questions.add(other_author)

        result = await service.browse(
            BrowseAuthorQuestionsInput(organization_id=org_id, author_id=author_id)
        )
        assert [item.question_id for item in result.items] == [matching.id]

    async def test_excludes_unpublished_questions(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = BrowseAuthorQuestionsService(question_repository=questions)
        org_id, author_id = uuid4(), uuid4()
        published = _make_published_question(organization_id=org_id, author_id=author_id)
        draft = CommunityQuestion.create(
            community_id=uuid4(),
            organization_id=org_id,
            author_id=author_id,
            primary_topic_id=uuid4(),
            title=QuestionTitle("Draft"),
            body="Body",
        )
        await questions.add(published)
        await questions.add(draft)

        result = await service.browse(
            BrowseAuthorQuestionsInput(organization_id=org_id, author_id=author_id)
        )
        assert [item.question_id for item in result.items] == [published.id]

    async def test_includes_closed_questions(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = BrowseAuthorQuestionsService(question_repository=questions)
        org_id, author_id = uuid4(), uuid4()
        closed = _make_published_question(organization_id=org_id, author_id=author_id)
        closed.close()
        await questions.add(closed)

        result = await service.browse(
            BrowseAuthorQuestionsInput(organization_id=org_id, author_id=author_id)
        )
        assert [item.question_id for item in result.items] == [closed.id]

    async def test_scopes_to_organization(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = BrowseAuthorQuestionsService(question_repository=questions)
        org_id, author_id = uuid4(), uuid4()
        matching = _make_published_question(organization_id=org_id, author_id=author_id)
        other_org = _make_published_question(organization_id=uuid4(), author_id=author_id)
        await questions.add(matching)
        await questions.add(other_org)

        result = await service.browse(
            BrowseAuthorQuestionsInput(organization_id=org_id, author_id=author_id)
        )
        assert [item.question_id for item in result.items] == [matching.id]

    async def test_empty_feed_returns_no_items_and_no_cursor(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = BrowseAuthorQuestionsService(question_repository=questions)

        result = await service.browse(
            BrowseAuthorQuestionsInput(organization_id=uuid4(), author_id=uuid4())
        )
        assert result.items == ()
        assert result.next_cursor is None

    async def test_respects_limit(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = BrowseAuthorQuestionsService(question_repository=questions)
        org_id, author_id = uuid4(), uuid4()
        for _ in range(3):
            await questions.add(
                _make_published_question(organization_id=org_id, author_id=author_id)
            )

        result = await service.browse(
            BrowseAuthorQuestionsInput(organization_id=org_id, author_id=author_id, limit=2)
        )
        assert len(result.items) == 2
        assert result.next_cursor is not None

    async def test_cursor_pagination_covers_all_questions_without_duplicates(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = BrowseAuthorQuestionsService(question_repository=questions)
        org_id, author_id = uuid4(), uuid4()
        created = [
            _make_published_question(organization_id=org_id, author_id=author_id) for _ in range(5)
        ]
        for question in created:
            await questions.add(question)

        seen: list[object] = []
        cursor: str | None = None
        for _ in range(10):
            page = await service.browse(
                BrowseAuthorQuestionsInput(
                    organization_id=org_id, author_id=author_id, cursor=cursor, limit=2
                )
            )
            seen.extend(item.question_id for item in page.items)
            cursor = page.next_cursor
            if cursor is None:
                break

        assert sorted(seen, key=str) == sorted((q.id for q in created), key=str)
        assert len(seen) == len(set(seen))
