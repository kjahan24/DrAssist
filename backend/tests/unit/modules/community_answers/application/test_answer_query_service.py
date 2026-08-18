"""Unit tests for `GetAnswerService`/`ListAnswersService`, using
in-memory fakes. `GetAnswerService` is the one read path this module
enforces `AnswerVisibility` on; both services return the anonymous-
masked `CommunityAnswerSummaryDTO` — see that dataclass's own
docstring."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityMemberStatus, CommunityRole
from app.modules.community_answers.application.dto import ListAnswersInput
from app.modules.community_answers.application.services.answer_query_service import (
    GetAnswerService,
    ListAnswersService,
)
from app.modules.community_answers.domain.entities import CommunityAnswer
from app.modules.community_answers.domain.enums import AnswerStatus, AnswerVisibility
from app.modules.community_answers.domain.exceptions import AnswerNotViewableError
from app.modules.community_answers.domain.value_objects import AnswerBody
from tests.unit.modules.community_answers.application.fakes import (
    FakeCommunityAnswerRepository,
    FakeCommunityQueryPort,
    make_member_summary,
)


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


class TestGetAnswerById:
    async def test_returns_none_for_unknown_answer(self) -> None:
        answers = FakeCommunityAnswerRepository()
        communities = FakeCommunityQueryPort()
        service = GetAnswerService(answer_repository=answers, community_query_port=communities)

        result = await service.get_by_id(uuid4())
        assert result is None

    async def test_returns_a_public_answer_with_no_acting_user(self) -> None:
        answers = FakeCommunityAnswerRepository()
        communities = FakeCommunityQueryPort()
        answer = _make_answer(visibility=AnswerVisibility.PUBLIC)
        await answers.add(answer)
        service = GetAnswerService(answer_repository=answers, community_query_port=communities)

        result = await service.get_by_id(answer.id)
        assert result is not None
        assert result.answer_id == answer.id

    async def test_masks_author_id_for_an_anonymous_answer(self) -> None:
        answers = FakeCommunityAnswerRepository()
        communities = FakeCommunityQueryPort()
        answer = _make_answer(is_anonymous=True)
        await answers.add(answer)
        service = GetAnswerService(answer_repository=answers, community_query_port=communities)

        result = await service.get_by_id(answer.id, acting_user_id=answer.author_id)
        assert result is not None
        assert result.author_id is None

    async def test_does_not_mask_author_id_for_a_non_anonymous_answer(self) -> None:
        answers = FakeCommunityAnswerRepository()
        communities = FakeCommunityQueryPort()
        answer = _make_answer(is_anonymous=False)
        await answers.add(answer)
        service = GetAnswerService(answer_repository=answers, community_query_port=communities)

        result = await service.get_by_id(answer.id)
        assert result is not None
        assert result.author_id == answer.author_id

    async def test_raises_when_members_only_answer_viewed_by_non_member(self) -> None:
        answers = FakeCommunityAnswerRepository()
        communities = FakeCommunityQueryPort()
        answer = _make_answer(visibility=AnswerVisibility.MEMBERS_ONLY)
        await answers.add(answer)
        service = GetAnswerService(answer_repository=answers, community_query_port=communities)

        with pytest.raises(AnswerNotViewableError):
            await service.get_by_id(answer.id, acting_user_id=uuid4())

    async def test_allows_members_only_answer_for_active_member(self) -> None:
        answers = FakeCommunityAnswerRepository()
        communities = FakeCommunityQueryPort()
        answer = _make_answer(visibility=AnswerVisibility.MEMBERS_ONLY)
        await answers.add(answer)
        viewer_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=answer.community_id,
                user_id=viewer_id,
                role=CommunityRole.MEMBER,
                status=CommunityMemberStatus.ACTIVE,
            )
        )
        service = GetAnswerService(answer_repository=answers, community_query_port=communities)

        result = await service.get_by_id(answer.id, acting_user_id=viewer_id)
        assert result is not None

    async def test_private_answer_viewable_by_author(self) -> None:
        answers = FakeCommunityAnswerRepository()
        communities = FakeCommunityQueryPort()
        answer = _make_answer(visibility=AnswerVisibility.PRIVATE)
        await answers.add(answer)
        service = GetAnswerService(answer_repository=answers, community_query_port=communities)

        result = await service.get_by_id(answer.id, acting_user_id=answer.author_id)
        assert result is not None

    async def test_private_answer_not_viewable_by_plain_member(self) -> None:
        answers = FakeCommunityAnswerRepository()
        communities = FakeCommunityQueryPort()
        answer = _make_answer(visibility=AnswerVisibility.PRIVATE)
        await answers.add(answer)
        viewer_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=answer.community_id, user_id=viewer_id, role=CommunityRole.MEMBER
            )
        )
        service = GetAnswerService(answer_repository=answers, community_query_port=communities)

        with pytest.raises(AnswerNotViewableError):
            await service.get_by_id(answer.id, acting_user_id=viewer_id)

    async def test_private_answer_viewable_by_moderator(self) -> None:
        answers = FakeCommunityAnswerRepository()
        communities = FakeCommunityQueryPort()
        answer = _make_answer(visibility=AnswerVisibility.PRIVATE)
        await answers.add(answer)
        moderator_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=answer.community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )
        service = GetAnswerService(answer_repository=answers, community_query_port=communities)

        result = await service.get_by_id(answer.id, acting_user_id=moderator_id)
        assert result is not None


class TestListAnswers:
    async def test_lists_answers_scoped_to_organization(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = ListAnswersService(answer_repository=answers)
        org_id = uuid4()
        matching = _make_answer(organization_id=org_id)
        other_org = _make_answer()
        await answers.add(matching)
        await answers.add(other_org)

        result = await service.list_answers(ListAnswersInput(organization_id=org_id))
        assert result.total == 1
        assert result.items[0].answer_id == matching.id

    async def test_filters_by_question(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = ListAnswersService(answer_repository=answers)
        org_id, question_id = uuid4(), uuid4()
        matching = _make_answer(organization_id=org_id, question_id=question_id)
        other = _make_answer(organization_id=org_id)
        await answers.add(matching)
        await answers.add(other)

        result = await service.list_answers(
            ListAnswersInput(organization_id=org_id, question_id=question_id)
        )
        assert [i.answer_id for i in result.items] == [matching.id]

    async def test_filters_by_author(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = ListAnswersService(answer_repository=answers)
        org_id, author_id = uuid4(), uuid4()
        matching = _make_answer(organization_id=org_id, author_id=author_id)
        other = _make_answer(organization_id=org_id)
        await answers.add(matching)
        await answers.add(other)

        result = await service.list_answers(
            ListAnswersInput(organization_id=org_id, author_id=author_id)
        )
        assert [i.answer_id for i in result.items] == [matching.id]

    async def test_filters_by_topic(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = ListAnswersService(answer_repository=answers)
        org_id, topic_id = uuid4(), uuid4()
        matching = _make_answer(organization_id=org_id, topic_id=topic_id)
        other = _make_answer(organization_id=org_id)
        await answers.add(matching)
        await answers.add(other)

        result = await service.list_answers(
            ListAnswersInput(organization_id=org_id, topic_id=topic_id)
        )
        assert [i.answer_id for i in result.items] == [matching.id]

    async def test_filters_by_status(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = ListAnswersService(answer_repository=answers)
        org_id = uuid4()
        published = _make_answer(organization_id=org_id)
        published.publish()
        draft = _make_answer(organization_id=org_id)
        await answers.add(published)
        await answers.add(draft)

        result = await service.list_answers(
            ListAnswersInput(organization_id=org_id, status=(AnswerStatus.DRAFT,))
        )
        assert [i.answer_id for i in result.items] == [draft.id]

    async def test_excludes_deleted_answers_by_default(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = ListAnswersService(answer_repository=answers)
        org_id = uuid4()
        deleted = _make_answer(organization_id=org_id)
        deleted.delete()
        live = _make_answer(organization_id=org_id)
        await answers.add(deleted)
        await answers.add(live)

        result = await service.list_answers(ListAnswersInput(organization_id=org_id))
        assert [i.answer_id for i in result.items] == [live.id]

    async def test_include_deleted_true_includes_deleted_answers(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = ListAnswersService(answer_repository=answers)
        org_id = uuid4()
        deleted = _make_answer(organization_id=org_id)
        deleted.delete()
        await answers.add(deleted)

        result = await service.list_answers(
            ListAnswersInput(organization_id=org_id, include_deleted=True)
        )
        assert [i.answer_id for i in result.items] == [deleted.id]

    async def test_filters_best_answer_only(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = ListAnswersService(answer_repository=answers)
        org_id = uuid4()
        best = _make_answer(organization_id=org_id)
        best.publish()
        best.mark_as_best()
        other = _make_answer(organization_id=org_id)
        await answers.add(best)
        await answers.add(other)

        result = await service.list_answers(
            ListAnswersInput(organization_id=org_id, best_answer_only=True)
        )
        assert [i.answer_id for i in result.items] == [best.id]

    async def test_filters_featured_only(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = ListAnswersService(answer_repository=answers)
        org_id = uuid4()
        featured = _make_answer(organization_id=org_id)
        featured.set_featured(True)
        other = _make_answer(organization_id=org_id)
        await answers.add(featured)
        await answers.add(other)

        result = await service.list_answers(
            ListAnswersInput(organization_id=org_id, featured_only=True)
        )
        assert [i.answer_id for i in result.items] == [featured.id]

    async def test_filters_pinned_only(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = ListAnswersService(answer_repository=answers)
        org_id = uuid4()
        pinned = _make_answer(organization_id=org_id)
        pinned.set_pinned(True)
        other = _make_answer(organization_id=org_id)
        await answers.add(pinned)
        await answers.add(other)

        result = await service.list_answers(
            ListAnswersInput(organization_id=org_id, pinned_only=True)
        )
        assert [i.answer_id for i in result.items] == [pinned.id]

    async def test_masks_author_id_for_anonymous_answers_in_the_list(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = ListAnswersService(answer_repository=answers)
        org_id = uuid4()
        anonymous = _make_answer(organization_id=org_id, is_anonymous=True)
        await answers.add(anonymous)

        result = await service.list_answers(ListAnswersInput(organization_id=org_id))
        assert result.items[0].author_id is None

    async def test_respects_limit(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = ListAnswersService(answer_repository=answers)
        org_id = uuid4()
        for _ in range(3):
            await answers.add(_make_answer(organization_id=org_id))

        result = await service.list_answers(ListAnswersInput(organization_id=org_id, limit=2))
        assert result.total == 3
        assert len(result.items) == 2

    async def test_respects_offset(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = ListAnswersService(answer_repository=answers)
        org_id = uuid4()
        for _ in range(3):
            await answers.add(_make_answer(organization_id=org_id))

        result = await service.list_answers(
            ListAnswersInput(organization_id=org_id, limit=2, offset=2)
        )
        assert result.total == 3
        assert len(result.items) == 1

    async def test_sort_order_ascending_reverses_the_default_order(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = ListAnswersService(answer_repository=answers)
        org_id = uuid4()
        first = _make_answer(organization_id=org_id)
        second = _make_answer(organization_id=org_id)
        await answers.add(first)
        await answers.add(second)

        descending = await service.list_answers(
            ListAnswersInput(organization_id=org_id, sort_order="desc")
        )
        ascending = await service.list_answers(
            ListAnswersInput(organization_id=org_id, sort_order="asc")
        )
        assert [i.answer_id for i in ascending.items] == list(
            reversed([i.answer_id for i in descending.items])
        )

    async def test_filters_by_visibility(self) -> None:
        answers = FakeCommunityAnswerRepository()
        service = ListAnswersService(answer_repository=answers)
        org_id = uuid4()
        matching = _make_answer(organization_id=org_id, visibility=AnswerVisibility.MEMBERS_ONLY)
        other = _make_answer(organization_id=org_id, visibility=AnswerVisibility.PUBLIC)
        await answers.add(matching)
        await answers.add(other)

        result = await service.list_answers(
            ListAnswersInput(organization_id=org_id, visibility=(AnswerVisibility.MEMBERS_ONLY,))
        )
        assert [i.answer_id for i in result.items] == [matching.id]
