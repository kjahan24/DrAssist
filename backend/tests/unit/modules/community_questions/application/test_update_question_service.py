"""Unit tests for `UpdateQuestionService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityRole
from app.modules.community_questions.application.dto import UpdateQuestionInput
from app.modules.community_questions.application.services.update_question_service import (
    UpdateQuestionService,
)
from app.modules.community_questions.domain.entities import CommunityQuestion
from app.modules.community_questions.domain.enums import QuestionType, QuestionVisibility
from app.modules.community_questions.domain.events import CommunityQuestionUpdated
from app.modules.community_questions.domain.exceptions import (
    InsufficientQuestionRoleError,
    QuestionNotFoundError,
)
from app.modules.community_questions.domain.value_objects import QuestionSummary, QuestionTitle
from tests.unit.modules.community_questions.application.fakes import (
    FakeCommunityQueryPort,
    FakeCommunityQuestionRepository,
    FakeUnitOfWork,
    make_community_summary,
    make_member_summary,
)


def _seeded() -> (
    tuple[
        UpdateQuestionService,
        FakeCommunityQuestionRepository,
        FakeCommunityQueryPort,
        FakeUnitOfWork,
    ]
):
    questions = FakeCommunityQuestionRepository()
    communities = FakeCommunityQueryPort()
    uow = FakeUnitOfWork()
    service = UpdateQuestionService(
        question_repository=questions, community_query_port=communities, unit_of_work=uow
    )
    return service, questions, communities, uow


async def _seed_question(
    questions: FakeCommunityQuestionRepository,
    communities: FakeCommunityQueryPort,
    **overrides: object,
) -> CommunityQuestion:
    defaults: dict[str, object] = {
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "author_id": uuid4(),
        "primary_topic_id": uuid4(),
        "title": QuestionTitle("Original Title"),
        "body": "Original body.",
    }
    defaults.update(overrides)
    question = CommunityQuestion.create(**defaults)  # type: ignore[arg-type]
    await questions.add(question)
    communities.add_community(make_community_summary(community_id=question.community_id))
    return question


class TestUpdateQuestion:
    async def test_author_updates_the_title(self) -> None:
        service, questions, communities, _ = _seeded()
        question = await _seed_question(questions, communities)

        await service.execute(
            UpdateQuestionInput(
                question_id=question.id, acting_user_id=question.author_id, title="New Title"
            )
        )
        stored = await questions.get_by_id(question.id)
        assert stored is not None
        assert str(stored.title) == "New Title"

    async def test_author_updates_body(self) -> None:
        service, questions, communities, _ = _seeded()
        question = await _seed_question(questions, communities)

        await service.execute(
            UpdateQuestionInput(
                question_id=question.id, acting_user_id=question.author_id, body="New body content."
            )
        )
        stored = await questions.get_by_id(question.id)
        assert stored is not None
        assert stored.body == "New body content."

    async def test_moderator_can_update_someone_elses_question(self) -> None:
        service, questions, communities, _ = _seeded()
        question = await _seed_question(questions, communities)
        moderator_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=question.community_id,
                user_id=moderator_id,
                role=CommunityRole.MODERATOR,
            )
        )

        await service.execute(
            UpdateQuestionInput(
                question_id=question.id, acting_user_id=moderator_id, title="Moderator Edit"
            )
        )
        stored = await questions.get_by_id(question.id)
        assert stored is not None
        assert str(stored.title) == "Moderator Edit"

    async def test_plain_member_cannot_update_someone_elses_question(self) -> None:
        service, questions, communities, _ = _seeded()
        question = await _seed_question(questions, communities)
        member_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=question.community_id, user_id=member_id, role=CommunityRole.MEMBER
            )
        )

        with pytest.raises(InsufficientQuestionRoleError):
            await service.execute(
                UpdateQuestionInput(
                    question_id=question.id, acting_user_id=member_id, title="Unauthorized Edit"
                )
            )

    async def test_unknown_question_raises(self) -> None:
        service, _, _, _ = _seeded()
        with pytest.raises(QuestionNotFoundError):
            await service.execute(
                UpdateQuestionInput(question_id=uuid4(), acting_user_id=uuid4(), title="X")
            )

    async def test_updates_question_type_and_visibility(self) -> None:
        service, questions, communities, _ = _seeded()
        question = await _seed_question(questions, communities)

        await service.execute(
            UpdateQuestionInput(
                question_id=question.id,
                acting_user_id=question.author_id,
                question_type=QuestionType.RESEARCH_QUESTION,
                visibility=QuestionVisibility.MEMBERS_ONLY,
            )
        )
        stored = await questions.get_by_id(question.id)
        assert stored is not None
        assert stored.question_type is QuestionType.RESEARCH_QUESTION
        assert stored.visibility is QuestionVisibility.MEMBERS_ONLY

    async def test_explicit_summary_overrides_the_existing_one(self) -> None:
        service, questions, communities, _ = _seeded()
        question = await _seed_question(questions, communities)

        await service.execute(
            UpdateQuestionInput(
                question_id=question.id,
                acting_user_id=question.author_id,
                summary="A curated summary.",
            )
        )
        stored = await questions.get_by_id(question.id)
        assert stored is not None
        assert str(stored.summary) == "A curated summary."

    async def test_editing_body_alone_leaves_the_existing_summary_untouched(self) -> None:
        service, questions, communities, _ = _seeded()
        question = await _seed_question(
            questions, communities, summary=QuestionSummary("Curated summary.")
        )

        await service.execute(
            UpdateQuestionInput(
                question_id=question.id, acting_user_id=question.author_id, body="Brand new body."
            )
        )
        stored = await questions.get_by_id(question.id)
        assert stored is not None
        assert str(stored.summary) == "Curated summary."

    async def test_regenerate_summary_true_rederives_it_from_the_new_body(self) -> None:
        service, questions, communities, _ = _seeded()
        question = await _seed_question(
            questions, communities, summary=QuestionSummary("Stale summary.")
        )

        await service.execute(
            UpdateQuestionInput(
                question_id=question.id,
                acting_user_id=question.author_id,
                body="A freshly written replacement body.",
                regenerate_summary=True,
            )
        )
        stored = await questions.get_by_id(question.id)
        assert stored is not None
        assert str(stored.summary) == "A freshly written replacement body."

    async def test_body_change_recomputes_read_time_minutes(self) -> None:
        service, questions, communities, _ = _seeded()
        question = await _seed_question(questions, communities)

        await service.execute(
            UpdateQuestionInput(
                question_id=question.id,
                acting_user_id=question.author_id,
                body=" ".join(["word"] * 400),
            )
        )
        stored = await questions.get_by_id(question.id)
        assert stored is not None
        assert stored.read_time_minutes == 2

    async def test_updates_is_anonymous(self) -> None:
        service, questions, communities, _ = _seeded()
        question = await _seed_question(questions, communities)

        await service.execute(
            UpdateQuestionInput(
                question_id=question.id, acting_user_id=question.author_id, is_anonymous=True
            )
        )
        stored = await questions.get_by_id(question.id)
        assert stored is not None
        assert stored.is_anonymous is True

    async def test_tracks_updated_by(self) -> None:
        service, questions, communities, _ = _seeded()
        question = await _seed_question(questions, communities)

        await service.execute(
            UpdateQuestionInput(
                question_id=question.id, acting_user_id=question.author_id, title="New Title"
            )
        )
        stored = await questions.get_by_id(question.id)
        assert stored is not None
        assert stored.updated_by == question.author_id

    async def test_commits_the_unit_of_work(self) -> None:
        service, questions, communities, uow = _seeded()
        question = await _seed_question(questions, communities)

        await service.execute(
            UpdateQuestionInput(
                question_id=question.id, acting_user_id=question.author_id, title="New Title"
            )
        )
        assert uow.committed is True

    async def test_publishes_a_community_question_updated_event(self) -> None:
        service, questions, communities, uow = _seeded()
        question = await _seed_question(questions, communities)

        await service.execute(
            UpdateQuestionInput(
                question_id=question.id, acting_user_id=question.author_id, title="New Title"
            )
        )
        assert any(isinstance(e, CommunityQuestionUpdated) for e in uow.published_events)

    async def test_output_reflects_the_update(self) -> None:
        service, questions, communities, _ = _seeded()
        question = await _seed_question(questions, communities)

        output = await service.execute(
            UpdateQuestionInput(
                question_id=question.id, acting_user_id=question.author_id, title="Renamed"
            )
        )
        assert output.question_id == question.id
        assert output.title == "Renamed"
