"""Unit tests for `ManageQuestionTagsService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityRole
from app.modules.community_questions.application.dto import (
    AssignQuestionTagInput,
    UnassignQuestionTagInput,
)
from app.modules.community_questions.application.services.manage_question_tags_service import (
    ManageQuestionTagsService,
)
from app.modules.community_questions.domain.entities import CommunityQuestion
from app.modules.community_questions.domain.events import CommunityQuestionTagAssigned
from app.modules.community_questions.domain.exceptions import (
    DuplicateQuestionTagError,
    InsufficientQuestionRoleError,
    QuestionNotFoundError,
    QuestionTagNotFoundError,
)
from app.modules.community_questions.domain.value_objects import QuestionTitle
from tests.unit.modules.community_questions.application.fakes import (
    FakeCommunityQueryPort,
    FakeCommunityQuestionRepository,
    FakeCommunityQuestionTagRepository,
    FakeUnitOfWork,
    make_community_summary,
    make_member_summary,
)


def _seeded() -> (
    tuple[
        ManageQuestionTagsService,
        FakeCommunityQuestionRepository,
        FakeCommunityQuestionTagRepository,
        FakeCommunityQueryPort,
        FakeUnitOfWork,
    ]
):
    questions = FakeCommunityQuestionRepository()
    question_tags = FakeCommunityQuestionTagRepository()
    communities = FakeCommunityQueryPort()
    uow = FakeUnitOfWork()
    service = ManageQuestionTagsService(
        question_tag_repository=question_tags,
        question_repository=questions,
        community_query_port=communities,
        unit_of_work=uow,
    )
    return service, questions, question_tags, communities, uow


async def _seed_question(
    questions: FakeCommunityQuestionRepository, communities: FakeCommunityQueryPort
) -> CommunityQuestion:
    question = CommunityQuestion.create(
        community_id=uuid4(),
        organization_id=uuid4(),
        author_id=uuid4(),
        primary_topic_id=uuid4(),
        title=QuestionTitle("Title"),
        body="Body",
    )
    await questions.add(question)
    communities.add_community(make_community_summary(community_id=question.community_id))
    return question


class TestAssignTag:
    async def test_author_assigns_a_tag(self) -> None:
        service, questions, question_tags, communities, _ = _seeded()
        question = await _seed_question(questions, communities)

        summary = await service.assign_tag(
            AssignQuestionTagInput(
                question_id=question.id, acting_user_id=question.author_id, tag="Oncology"
            )
        )
        assert summary.tag == "oncology"
        assert len(await question_tags.list_by_question(question.id)) == 1

    async def test_plain_member_cannot_assign_tag_to_someone_elses_question(self) -> None:
        service, questions, _, communities, _ = _seeded()
        question = await _seed_question(questions, communities)
        member_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=question.community_id, user_id=member_id, role=CommunityRole.MEMBER
            )
        )

        with pytest.raises(InsufficientQuestionRoleError):
            await service.assign_tag(
                AssignQuestionTagInput(
                    question_id=question.id, acting_user_id=member_id, tag="oncology"
                )
            )

    async def test_unknown_question_raises(self) -> None:
        service, _, _, _, _ = _seeded()
        with pytest.raises(QuestionNotFoundError):
            await service.assign_tag(
                AssignQuestionTagInput(question_id=uuid4(), acting_user_id=uuid4(), tag="oncology")
            )

    async def test_duplicate_tag_raises(self) -> None:
        service, questions, _, communities, _ = _seeded()
        question = await _seed_question(questions, communities)
        await service.assign_tag(
            AssignQuestionTagInput(
                question_id=question.id, acting_user_id=question.author_id, tag="oncology"
            )
        )

        with pytest.raises(DuplicateQuestionTagError):
            await service.assign_tag(
                AssignQuestionTagInput(
                    question_id=question.id, acting_user_id=question.author_id, tag="Oncology"
                )
            )

    async def test_commits_and_publishes_event(self) -> None:
        service, questions, _, communities, uow = _seeded()
        question = await _seed_question(questions, communities)

        await service.assign_tag(
            AssignQuestionTagInput(
                question_id=question.id, acting_user_id=question.author_id, tag="oncology"
            )
        )
        assert uow.committed is True
        assert any(isinstance(e, CommunityQuestionTagAssigned) for e in uow.published_events)


class TestListTags:
    async def test_lists_assigned_tags(self) -> None:
        service, questions, _, communities, _ = _seeded()
        question = await _seed_question(questions, communities)
        await service.assign_tag(
            AssignQuestionTagInput(
                question_id=question.id, acting_user_id=question.author_id, tag="oncology"
            )
        )

        result = await service.list_tags(question.id)
        assert [t.tag for t in result] == ["oncology"]

    async def test_returns_empty_for_a_question_with_no_tags(self) -> None:
        service, questions, _, communities, _ = _seeded()
        question = await _seed_question(questions, communities)

        assert await service.list_tags(question.id) == []


class TestUnassignTag:
    async def test_author_unassigns_a_tag(self) -> None:
        service, questions, _, communities, _ = _seeded()
        question = await _seed_question(questions, communities)
        assignment = await service.assign_tag(
            AssignQuestionTagInput(
                question_id=question.id, acting_user_id=question.author_id, tag="oncology"
            )
        )

        await service.unassign_tag(
            UnassignQuestionTagInput(
                question_id=question.id,
                acting_user_id=question.author_id,
                question_tag_id=assignment.question_tag_id,
            )
        )
        assert await service.list_tags(question.id) == []

    async def test_moderator_unassigns_a_tag_from_someone_elses_question(self) -> None:
        service, questions, _, communities, _ = _seeded()
        question = await _seed_question(questions, communities)
        assignment = await service.assign_tag(
            AssignQuestionTagInput(
                question_id=question.id, acting_user_id=question.author_id, tag="oncology"
            )
        )
        moderator_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=question.community_id,
                user_id=moderator_id,
                role=CommunityRole.MODERATOR,
            )
        )

        await service.unassign_tag(
            UnassignQuestionTagInput(
                question_id=question.id,
                acting_user_id=moderator_id,
                question_tag_id=assignment.question_tag_id,
            )
        )
        assert await service.list_tags(question.id) == []

    async def test_unknown_assignment_raises(self) -> None:
        service, questions, _, communities, _ = _seeded()
        question = await _seed_question(questions, communities)

        with pytest.raises(QuestionTagNotFoundError):
            await service.unassign_tag(
                UnassignQuestionTagInput(
                    question_id=question.id,
                    acting_user_id=question.author_id,
                    question_tag_id=uuid4(),
                )
            )
