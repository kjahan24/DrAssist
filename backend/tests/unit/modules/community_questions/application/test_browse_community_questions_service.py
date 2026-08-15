"""Unit tests for `BrowseCommunityQuestionsService`, using in-memory
fakes.

Covers the `pinned_first=True` behavior (pinned questions surfaced once
on page 1 only) and cursor pagination across multiple pages, plus the
PUBLISHED+CLOSED "live feed" status inclusion — see
`CommunityQuestionRepository.browse_feed`'s own docstring for the
contract these tests are pinned against.
"""

from uuid import uuid4

import pytest

from app.modules.community_questions.application.dto import BrowseCommunityQuestionsInput
from app.modules.community_questions.application.services.browse_community_questions_service import (  # noqa: E501
    BrowseCommunityQuestionsService,
)
from app.modules.community_questions.domain.entities import CommunityQuestion
from app.modules.community_questions.domain.exceptions import CommunityNotFoundForQuestionError
from app.modules.community_questions.domain.value_objects import QuestionTitle
from tests.unit.modules.community_questions.application.fakes import (
    FakeCommunityQueryPort,
    FakeCommunityQuestionRepository,
    make_community_summary,
)


def _make_published_question(*, community_id: object, organization_id: object) -> CommunityQuestion:
    question = CommunityQuestion.create(
        community_id=community_id,  # type: ignore[arg-type]
        organization_id=organization_id,  # type: ignore[arg-type]
        author_id=uuid4(),
        primary_topic_id=uuid4(),
        title=QuestionTitle("Title"),
        body="Body",
    )
    question.publish()
    return question


class TestBrowseCommunityQuestions:
    async def test_raises_when_community_unknown(self) -> None:
        questions = FakeCommunityQuestionRepository()
        communities = FakeCommunityQueryPort()
        service = BrowseCommunityQuestionsService(
            question_repository=questions, community_query_port=communities
        )

        with pytest.raises(CommunityNotFoundForQuestionError):
            await service.browse(BrowseCommunityQuestionsInput(community_id=uuid4()))

    async def test_returns_only_published_and_closed_questions_in_the_community(self) -> None:
        questions = FakeCommunityQuestionRepository()
        communities = FakeCommunityQueryPort()
        community_id, org_id = uuid4(), uuid4()
        communities.add_community(
            make_community_summary(community_id=community_id, organization_id=org_id)
        )
        published = _make_published_question(community_id=community_id, organization_id=org_id)
        closed = _make_published_question(community_id=community_id, organization_id=org_id)
        closed.close()
        draft = CommunityQuestion.create(
            community_id=community_id,
            organization_id=org_id,
            author_id=uuid4(),
            primary_topic_id=uuid4(),
            title=QuestionTitle("Draft"),
            body="Body",
        )
        other_community = _make_published_question(community_id=uuid4(), organization_id=org_id)
        for q in (published, closed, draft, other_community):
            await questions.add(q)
        service = BrowseCommunityQuestionsService(
            question_repository=questions, community_query_port=communities
        )

        result = await service.browse(BrowseCommunityQuestionsInput(community_id=community_id))
        ids = {item.question_id for item in result.items}
        assert ids == {published.id, closed.id}

    async def test_pinned_questions_are_surfaced_first_on_page_one(self) -> None:
        questions = FakeCommunityQuestionRepository()
        communities = FakeCommunityQueryPort()
        community_id, org_id = uuid4(), uuid4()
        communities.add_community(
            make_community_summary(community_id=community_id, organization_id=org_id)
        )
        regular = _make_published_question(community_id=community_id, organization_id=org_id)
        pinned = _make_published_question(community_id=community_id, organization_id=org_id)
        pinned.set_pinned(True)
        await questions.add(regular)
        await questions.add(pinned)
        service = BrowseCommunityQuestionsService(
            question_repository=questions, community_query_port=communities
        )

        result = await service.browse(BrowseCommunityQuestionsInput(community_id=community_id))
        assert result.items[0].question_id == pinned.id

    async def test_pinned_question_not_reinjected_on_second_page(self) -> None:
        questions = FakeCommunityQuestionRepository()
        communities = FakeCommunityQueryPort()
        community_id, org_id = uuid4(), uuid4()
        communities.add_community(
            make_community_summary(community_id=community_id, organization_id=org_id)
        )
        pinned = _make_published_question(community_id=community_id, organization_id=org_id)
        pinned.set_pinned(True)
        regular_questions = [
            _make_published_question(community_id=community_id, organization_id=org_id)
            for _ in range(2)
        ]
        await questions.add(pinned)
        for question in regular_questions:
            await questions.add(question)
        service = BrowseCommunityQuestionsService(
            question_repository=questions, community_query_port=communities
        )

        first_page = await service.browse(
            BrowseCommunityQuestionsInput(community_id=community_id, limit=2)
        )
        assert first_page.next_cursor is not None

        second_page = await service.browse(
            BrowseCommunityQuestionsInput(
                community_id=community_id, cursor=first_page.next_cursor, limit=2
            )
        )
        assert pinned.id not in [item.question_id for item in second_page.items]

    async def test_cursor_pagination_covers_all_questions_without_duplicates(self) -> None:
        questions = FakeCommunityQuestionRepository()
        communities = FakeCommunityQueryPort()
        community_id, org_id = uuid4(), uuid4()
        communities.add_community(
            make_community_summary(community_id=community_id, organization_id=org_id)
        )
        created = [
            _make_published_question(community_id=community_id, organization_id=org_id)
            for _ in range(5)
        ]
        for question in created:
            await questions.add(question)
        service = BrowseCommunityQuestionsService(
            question_repository=questions, community_query_port=communities
        )

        seen: list[object] = []
        cursor: str | None = None
        for _ in range(10):
            page = await service.browse(
                BrowseCommunityQuestionsInput(community_id=community_id, cursor=cursor, limit=2)
            )
            seen.extend(item.question_id for item in page.items)
            cursor = page.next_cursor
            if cursor is None:
                break

        assert sorted(seen, key=str) == sorted((q.id for q in created), key=str)
        assert len(seen) == len(set(seen))
