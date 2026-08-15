"""Unit tests for `GetQuestionService`/`ListQuestionsService`, using
in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityMemberStatus, CommunityRole
from app.modules.community_questions.application.dto import ListQuestionsInput
from app.modules.community_questions.application.services.question_query_service import (
    GetQuestionService,
    ListQuestionsService,
)
from app.modules.community_questions.domain.entities import CommunityQuestion
from app.modules.community_questions.domain.enums import (
    QuestionStatus,
    QuestionType,
    QuestionVisibility,
)
from app.modules.community_questions.domain.exceptions import QuestionNotViewableError
from app.modules.community_questions.domain.value_objects import QuestionTitle
from tests.unit.modules.community_questions.application.fakes import (
    FakeCommunityQueryPort,
    FakeCommunityQuestionRepository,
    make_member_summary,
)


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


class TestGetQuestionById:
    async def test_returns_none_for_unknown_question(self) -> None:
        questions = FakeCommunityQuestionRepository()
        communities = FakeCommunityQueryPort()
        service = GetQuestionService(
            question_repository=questions, community_query_port=communities
        )

        result = await service.get_by_id(uuid4())
        assert result is None

    async def test_returns_a_public_question_with_no_acting_user(self) -> None:
        questions = FakeCommunityQuestionRepository()
        communities = FakeCommunityQueryPort()
        question = _make_question(visibility=QuestionVisibility.PUBLIC)
        await questions.add(question)
        service = GetQuestionService(
            question_repository=questions, community_query_port=communities
        )

        result = await service.get_by_id(question.id)
        assert result is not None
        assert result.question_id == question.id

    async def test_raises_when_members_only_question_viewed_by_non_member(self) -> None:
        questions = FakeCommunityQuestionRepository()
        communities = FakeCommunityQueryPort()
        question = _make_question(visibility=QuestionVisibility.MEMBERS_ONLY)
        await questions.add(question)
        service = GetQuestionService(
            question_repository=questions, community_query_port=communities
        )

        with pytest.raises(QuestionNotViewableError):
            await service.get_by_id(question.id, acting_user_id=uuid4())

    async def test_allows_members_only_question_for_active_member(self) -> None:
        questions = FakeCommunityQuestionRepository()
        communities = FakeCommunityQueryPort()
        question = _make_question(visibility=QuestionVisibility.MEMBERS_ONLY)
        await questions.add(question)
        viewer_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=question.community_id,
                user_id=viewer_id,
                role=CommunityRole.MEMBER,
                status=CommunityMemberStatus.ACTIVE,
            )
        )
        service = GetQuestionService(
            question_repository=questions, community_query_port=communities
        )

        result = await service.get_by_id(question.id, acting_user_id=viewer_id)
        assert result is not None

    async def test_private_question_viewable_by_author(self) -> None:
        questions = FakeCommunityQuestionRepository()
        communities = FakeCommunityQueryPort()
        question = _make_question(visibility=QuestionVisibility.PRIVATE)
        await questions.add(question)
        service = GetQuestionService(
            question_repository=questions, community_query_port=communities
        )

        result = await service.get_by_id(question.id, acting_user_id=question.author_id)
        assert result is not None

    async def test_private_question_not_viewable_by_plain_member(self) -> None:
        questions = FakeCommunityQuestionRepository()
        communities = FakeCommunityQueryPort()
        question = _make_question(visibility=QuestionVisibility.PRIVATE)
        await questions.add(question)
        viewer_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=question.community_id, user_id=viewer_id, role=CommunityRole.MEMBER
            )
        )
        service = GetQuestionService(
            question_repository=questions, community_query_port=communities
        )

        with pytest.raises(QuestionNotViewableError):
            await service.get_by_id(question.id, acting_user_id=viewer_id)

    async def test_private_question_viewable_by_moderator(self) -> None:
        questions = FakeCommunityQuestionRepository()
        communities = FakeCommunityQueryPort()
        question = _make_question(visibility=QuestionVisibility.PRIVATE)
        await questions.add(question)
        moderator_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=question.community_id,
                user_id=moderator_id,
                role=CommunityRole.MODERATOR,
            )
        )
        service = GetQuestionService(
            question_repository=questions, community_query_port=communities
        )

        result = await service.get_by_id(question.id, acting_user_id=moderator_id)
        assert result is not None


class TestGetQuestionBySlug:
    async def test_returns_none_for_unknown_slug(self) -> None:
        questions = FakeCommunityQuestionRepository()
        communities = FakeCommunityQueryPort()
        service = GetQuestionService(
            question_repository=questions, community_query_port=communities
        )

        result = await service.get_by_slug(uuid4(), "does-not-exist")
        assert result is None

    async def test_returns_the_matching_public_question(self) -> None:
        questions = FakeCommunityQuestionRepository()
        communities = FakeCommunityQueryPort()
        question = _make_question(visibility=QuestionVisibility.PUBLIC)
        await questions.add(question)
        service = GetQuestionService(
            question_repository=questions, community_query_port=communities
        )

        result = await service.get_by_slug(question.community_id, str(question.slug))
        assert result is not None
        assert result.slug == str(question.slug)


class TestListQuestions:
    async def test_lists_questions_scoped_to_organization(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = ListQuestionsService(question_repository=questions)
        org_id = uuid4()
        matching = _make_question(organization_id=org_id)
        other_org = _make_question()
        await questions.add(matching)
        await questions.add(other_org)

        result = await service.list_questions(ListQuestionsInput(organization_id=org_id))
        assert result.total == 1
        assert result.items[0].question_id == matching.id

    async def test_filters_by_community(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = ListQuestionsService(question_repository=questions)
        org_id = uuid4()
        community_id = uuid4()
        matching = _make_question(organization_id=org_id, community_id=community_id)
        other = _make_question(organization_id=org_id)
        await questions.add(matching)
        await questions.add(other)

        result = await service.list_questions(
            ListQuestionsInput(organization_id=org_id, community_id=community_id)
        )
        assert result.total == 1
        assert result.items[0].question_id == matching.id

    async def test_filters_by_author(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = ListQuestionsService(question_repository=questions)
        org_id, author_id = uuid4(), uuid4()
        matching = _make_question(organization_id=org_id, author_id=author_id)
        other = _make_question(organization_id=org_id)
        await questions.add(matching)
        await questions.add(other)

        result = await service.list_questions(
            ListQuestionsInput(organization_id=org_id, author_id=author_id)
        )
        assert [i.question_id for i in result.items] == [matching.id]

    async def test_filters_by_primary_topic(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = ListQuestionsService(question_repository=questions)
        org_id, topic_id = uuid4(), uuid4()
        matching = _make_question(organization_id=org_id, primary_topic_id=topic_id)
        other = _make_question(organization_id=org_id)
        await questions.add(matching)
        await questions.add(other)

        result = await service.list_questions(
            ListQuestionsInput(organization_id=org_id, topic_id=topic_id)
        )
        assert [i.question_id for i in result.items] == [matching.id]

    async def test_filters_by_secondary_topic(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = ListQuestionsService(question_repository=questions)
        org_id, topic_id = uuid4(), uuid4()
        matching = _make_question(organization_id=org_id)
        questions.assign_topic_for_search(matching.id, topic_id)
        other = _make_question(organization_id=org_id)
        await questions.add(matching)
        await questions.add(other)

        result = await service.list_questions(
            ListQuestionsInput(organization_id=org_id, topic_id=topic_id)
        )
        assert [i.question_id for i in result.items] == [matching.id]

    async def test_filters_by_question_type(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = ListQuestionsService(question_repository=questions)
        org_id = uuid4()
        matching = _make_question(organization_id=org_id, question_type=QuestionType.CLINICAL)
        other = _make_question(organization_id=org_id, question_type=QuestionType.GENERAL)
        await questions.add(matching)
        await questions.add(other)

        result = await service.list_questions(
            ListQuestionsInput(organization_id=org_id, question_type=(QuestionType.CLINICAL,))
        )
        assert [i.question_id for i in result.items] == [matching.id]

    async def test_filters_by_status(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = ListQuestionsService(question_repository=questions)
        org_id = uuid4()
        published = _make_question(organization_id=org_id)
        published.publish()
        draft = _make_question(organization_id=org_id)
        await questions.add(published)
        await questions.add(draft)

        result = await service.list_questions(
            ListQuestionsInput(organization_id=org_id, status=(QuestionStatus.DRAFT,))
        )
        assert [i.question_id for i in result.items] == [draft.id]

    async def test_excludes_deleted_questions_by_default(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = ListQuestionsService(question_repository=questions)
        org_id = uuid4()
        deleted = _make_question(organization_id=org_id)
        deleted.delete()
        live = _make_question(organization_id=org_id)
        await questions.add(deleted)
        await questions.add(live)

        result = await service.list_questions(ListQuestionsInput(organization_id=org_id))
        assert [i.question_id for i in result.items] == [live.id]

    async def test_include_deleted_true_includes_deleted_questions(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = ListQuestionsService(question_repository=questions)
        org_id = uuid4()
        deleted = _make_question(organization_id=org_id)
        deleted.delete()
        await questions.add(deleted)

        result = await service.list_questions(
            ListQuestionsInput(organization_id=org_id, include_deleted=True)
        )
        assert [i.question_id for i in result.items] == [deleted.id]

    async def test_filters_by_visibility(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = ListQuestionsService(question_repository=questions)
        org_id = uuid4()
        matching = _make_question(
            organization_id=org_id, visibility=QuestionVisibility.MEMBERS_ONLY
        )
        other = _make_question(organization_id=org_id, visibility=QuestionVisibility.PUBLIC)
        await questions.add(matching)
        await questions.add(other)

        result = await service.list_questions(
            ListQuestionsInput(
                organization_id=org_id, visibility=(QuestionVisibility.MEMBERS_ONLY,)
            )
        )
        assert [i.question_id for i in result.items] == [matching.id]

    async def test_filters_pinned_only(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = ListQuestionsService(question_repository=questions)
        org_id = uuid4()
        pinned = _make_question(organization_id=org_id)
        pinned.set_pinned(True)
        other = _make_question(organization_id=org_id)
        await questions.add(pinned)
        await questions.add(other)

        result = await service.list_questions(
            ListQuestionsInput(organization_id=org_id, pinned_only=True)
        )
        assert [i.question_id for i in result.items] == [pinned.id]

    async def test_filters_featured_only(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = ListQuestionsService(question_repository=questions)
        org_id = uuid4()
        featured = _make_question(organization_id=org_id)
        featured.set_featured(True)
        other = _make_question(organization_id=org_id)
        await questions.add(featured)
        await questions.add(other)

        result = await service.list_questions(
            ListQuestionsInput(organization_id=org_id, featured_only=True)
        )
        assert [i.question_id for i in result.items] == [featured.id]

    async def test_respects_limit(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = ListQuestionsService(question_repository=questions)
        org_id = uuid4()
        for _ in range(3):
            await questions.add(_make_question(organization_id=org_id))

        result = await service.list_questions(ListQuestionsInput(organization_id=org_id, limit=2))
        assert result.total == 3
        assert len(result.items) == 2

    async def test_respects_offset(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = ListQuestionsService(question_repository=questions)
        org_id = uuid4()
        for _ in range(3):
            await questions.add(_make_question(organization_id=org_id))

        result = await service.list_questions(
            ListQuestionsInput(organization_id=org_id, limit=2, offset=2)
        )
        assert result.total == 3
        assert len(result.items) == 1

    async def test_sort_order_ascending_reverses_the_default_order(self) -> None:
        questions = FakeCommunityQuestionRepository()
        service = ListQuestionsService(question_repository=questions)
        org_id = uuid4()
        first = _make_question(organization_id=org_id)
        second = _make_question(organization_id=org_id)
        await questions.add(first)
        await questions.add(second)

        descending = await service.list_questions(
            ListQuestionsInput(organization_id=org_id, sort_order="desc")
        )
        ascending = await service.list_questions(
            ListQuestionsInput(organization_id=org_id, sort_order="asc")
        )
        assert [i.question_id for i in ascending.items] == list(
            reversed([i.question_id for i in descending.items])
        )
