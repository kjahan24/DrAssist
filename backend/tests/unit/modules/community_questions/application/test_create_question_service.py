"""Unit tests for `CreateQuestionService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community_questions.application.dto import CreateQuestionInput
from app.modules.community_questions.application.services.create_question_service import (
    CreateQuestionService,
)
from app.modules.community_questions.domain.enums import (
    QuestionStatus,
    QuestionType,
    QuestionVisibility,
)
from app.modules.community_questions.domain.events import CommunityQuestionCreated
from app.modules.community_questions.domain.exceptions import (
    CommunityNotFoundForQuestionError,
    DuplicateQuestionTagError,
    DuplicateQuestionTopicError,
    QuestionMembershipRequiredError,
    TopicNotFoundForQuestionError,
)
from tests.unit.modules.community_questions.application.fakes import (
    FakeCommunityQueryPort,
    FakeCommunityQuestionRepository,
    FakeCommunityQuestionTagRepository,
    FakeCommunityQuestionTopicRepository,
    FakeTopicQueryPort,
    FakeUnitOfWork,
    make_community_summary,
    make_member_summary,
)


def _seeded() -> (
    tuple[
        CreateQuestionService,
        FakeCommunityQuestionRepository,
        FakeCommunityQuestionTopicRepository,
        FakeCommunityQuestionTagRepository,
        FakeCommunityQueryPort,
        FakeTopicQueryPort,
        FakeUnitOfWork,
    ]
):
    questions = FakeCommunityQuestionRepository()
    question_topics = FakeCommunityQuestionTopicRepository()
    question_tags = FakeCommunityQuestionTagRepository()
    communities = FakeCommunityQueryPort()
    topics = FakeTopicQueryPort()
    uow = FakeUnitOfWork()
    service = CreateQuestionService(
        question_repository=questions,
        question_topic_repository=question_topics,
        question_tag_repository=question_tags,
        community_query_port=communities,
        topic_query_port=topics,
        unit_of_work=uow,
    )
    return service, questions, question_topics, question_tags, communities, topics, uow


def _seed_membership(
    communities: FakeCommunityQueryPort, *, community_id: object, user_id: object
) -> None:
    communities.add_community(make_community_summary(community_id=community_id))
    communities.add_membership(make_member_summary(community_id=community_id, user_id=user_id))


class TestCreateQuestion:
    async def test_creates_a_question(self) -> None:
        service, questions, _, _, communities, topics, _ = _seeded()
        community_id, author_id, primary_topic_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        topics.add_topic(primary_topic_id)

        output = await service.execute(
            CreateQuestionInput(
                community_id=community_id,
                author_id=author_id,
                primary_topic_id=primary_topic_id,
                title="How should hypertension be managed?",
                body="This is the body of the question.",
            )
        )
        stored = await questions.get_by_id(output.question_id)
        assert stored is not None
        assert str(stored.title) == "How should hypertension be managed?"
        assert stored.primary_topic_id == primary_topic_id

    async def test_new_question_defaults_to_draft_status(self) -> None:
        service, _, _, _, communities, topics, _ = _seeded()
        community_id, author_id, primary_topic_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        topics.add_topic(primary_topic_id)

        output = await service.execute(
            CreateQuestionInput(
                community_id=community_id,
                author_id=author_id,
                primary_topic_id=primary_topic_id,
                title="Title",
                body="Body",
            )
        )
        assert output.status is QuestionStatus.DRAFT

    async def test_generates_a_slug_from_the_title(self) -> None:
        service, _, _, _, communities, topics, _ = _seeded()
        community_id, author_id, primary_topic_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        topics.add_topic(primary_topic_id)

        output = await service.execute(
            CreateQuestionInput(
                community_id=community_id,
                author_id=author_id,
                primary_topic_id=primary_topic_id,
                title="Hello World",
                body="Body",
            )
        )
        assert output.slug == "hello-world"

    async def test_duplicate_slug_within_the_same_community_is_disambiguated(self) -> None:
        service, _, _, _, communities, topics, _ = _seeded()
        community_id, author_id, primary_topic_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        topics.add_topic(primary_topic_id)

        first = await service.execute(
            CreateQuestionInput(
                community_id=community_id,
                author_id=author_id,
                primary_topic_id=primary_topic_id,
                title="Hello World",
                body="Body one",
            )
        )
        second = await service.execute(
            CreateQuestionInput(
                community_id=community_id,
                author_id=author_id,
                primary_topic_id=primary_topic_id,
                title="Hello World",
                body="Body two",
            )
        )
        assert first.slug != second.slug
        assert second.slug.startswith("hello-world")

    async def test_accepts_an_explicit_slug(self) -> None:
        service, _, _, _, communities, topics, _ = _seeded()
        community_id, author_id, primary_topic_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        topics.add_topic(primary_topic_id)

        output = await service.execute(
            CreateQuestionInput(
                community_id=community_id,
                author_id=author_id,
                primary_topic_id=primary_topic_id,
                title="Title",
                body="Body",
                slug="custom-slug",
            )
        )
        assert output.slug == "custom-slug"

    async def test_accepts_an_explicit_summary(self) -> None:
        service, questions, _, _, communities, topics, _ = _seeded()
        community_id, author_id, primary_topic_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        topics.add_topic(primary_topic_id)

        output = await service.execute(
            CreateQuestionInput(
                community_id=community_id,
                author_id=author_id,
                primary_topic_id=primary_topic_id,
                title="Title",
                body="Body",
                summary="A hand-written summary.",
            )
        )
        stored = await questions.get_by_id(output.question_id)
        assert stored is not None
        assert str(stored.summary) == "A hand-written summary."

    async def test_accepts_an_explicit_visibility(self) -> None:
        service, _, _, _, communities, topics, _ = _seeded()
        community_id, author_id, primary_topic_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        topics.add_topic(primary_topic_id)

        output = await service.execute(
            CreateQuestionInput(
                community_id=community_id,
                author_id=author_id,
                primary_topic_id=primary_topic_id,
                title="Title",
                body="Body",
                visibility=QuestionVisibility.PRIVATE,
            )
        )
        assert output.question_id is not None

    async def test_accepts_explicit_question_type(self) -> None:
        service, questions, _, _, communities, topics, _ = _seeded()
        community_id, author_id, primary_topic_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        topics.add_topic(primary_topic_id)

        output = await service.execute(
            CreateQuestionInput(
                community_id=community_id,
                author_id=author_id,
                primary_topic_id=primary_topic_id,
                title="Title",
                body="Body",
                question_type=QuestionType.CLINICAL,
            )
        )
        stored = await questions.get_by_id(output.question_id)
        assert stored is not None
        assert stored.question_type is QuestionType.CLINICAL

    async def test_assigns_initial_secondary_topics(self) -> None:
        service, _, question_topics, _, communities, topics, _ = _seeded()
        community_id, author_id, primary_topic_id = uuid4(), uuid4(), uuid4()
        secondary_topic_id = uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        topics.add_topic(primary_topic_id)
        topics.add_topic(secondary_topic_id)

        output = await service.execute(
            CreateQuestionInput(
                community_id=community_id,
                author_id=author_id,
                primary_topic_id=primary_topic_id,
                title="Title",
                body="Body",
                secondary_topic_ids=(secondary_topic_id,),
            )
        )
        assignments = await question_topics.list_by_question(output.question_id)
        assert [a.topic_id for a in assignments] == [secondary_topic_id]

    async def test_unknown_primary_topic_id_raises(self) -> None:
        service, _, _, _, communities, _, _ = _seeded()
        community_id, author_id = uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)

        with pytest.raises(TopicNotFoundForQuestionError):
            await service.execute(
                CreateQuestionInput(
                    community_id=community_id,
                    author_id=author_id,
                    primary_topic_id=uuid4(),
                    title="Title",
                    body="Body",
                )
            )

    async def test_unknown_secondary_topic_id_raises(self) -> None:
        service, _, _, _, communities, topics, _ = _seeded()
        community_id, author_id, primary_topic_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        topics.add_topic(primary_topic_id)

        with pytest.raises(TopicNotFoundForQuestionError):
            await service.execute(
                CreateQuestionInput(
                    community_id=community_id,
                    author_id=author_id,
                    primary_topic_id=primary_topic_id,
                    title="Title",
                    body="Body",
                    secondary_topic_ids=(uuid4(),),
                )
            )

    async def test_secondary_topic_equal_to_primary_topic_raises(self) -> None:
        service, _, _, _, communities, topics, _ = _seeded()
        community_id, author_id, primary_topic_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        topics.add_topic(primary_topic_id)

        with pytest.raises(DuplicateQuestionTopicError):
            await service.execute(
                CreateQuestionInput(
                    community_id=community_id,
                    author_id=author_id,
                    primary_topic_id=primary_topic_id,
                    title="Title",
                    body="Body",
                    secondary_topic_ids=(primary_topic_id,),
                )
            )

    async def test_duplicate_secondary_topic_id_raises(self) -> None:
        service, _, _, _, communities, topics, _ = _seeded()
        community_id, author_id, primary_topic_id = uuid4(), uuid4(), uuid4()
        secondary_topic_id = uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        topics.add_topic(primary_topic_id)
        topics.add_topic(secondary_topic_id)

        with pytest.raises(DuplicateQuestionTopicError):
            await service.execute(
                CreateQuestionInput(
                    community_id=community_id,
                    author_id=author_id,
                    primary_topic_id=primary_topic_id,
                    title="Title",
                    body="Body",
                    secondary_topic_ids=(secondary_topic_id, secondary_topic_id),
                )
            )

    async def test_assigns_initial_tags(self) -> None:
        service, _, _, question_tags, communities, topics, _ = _seeded()
        community_id, author_id, primary_topic_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        topics.add_topic(primary_topic_id)

        output = await service.execute(
            CreateQuestionInput(
                community_id=community_id,
                author_id=author_id,
                primary_topic_id=primary_topic_id,
                title="Title",
                body="Body",
                tags=("diabetes", "insulin"),
            )
        )
        assignments = await question_tags.list_by_question(output.question_id)
        assert {a.tag for a in assignments} == {"diabetes", "insulin"}

    async def test_duplicate_tag_in_initial_tags_raises(self) -> None:
        service, _, _, _, communities, topics, _ = _seeded()
        community_id, author_id, primary_topic_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        topics.add_topic(primary_topic_id)

        with pytest.raises(DuplicateQuestionTagError):
            await service.execute(
                CreateQuestionInput(
                    community_id=community_id,
                    author_id=author_id,
                    primary_topic_id=primary_topic_id,
                    title="Title",
                    body="Body",
                    tags=("oncology", "Oncology"),
                )
            )

    async def test_unknown_community_raises(self) -> None:
        service, _, _, _, _, _, _ = _seeded()
        with pytest.raises(CommunityNotFoundForQuestionError):
            await service.execute(
                CreateQuestionInput(
                    community_id=uuid4(),
                    author_id=uuid4(),
                    primary_topic_id=uuid4(),
                    title="Title",
                    body="Body",
                )
            )

    async def test_non_member_raises(self) -> None:
        service, _, _, _, communities, _, _ = _seeded()
        community_id = uuid4()
        communities.add_community(make_community_summary(community_id=community_id))

        with pytest.raises(QuestionMembershipRequiredError):
            await service.execute(
                CreateQuestionInput(
                    community_id=community_id,
                    author_id=uuid4(),
                    primary_topic_id=uuid4(),
                    title="Title",
                    body="Body",
                )
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, _, _, communities, topics, uow = _seeded()
        community_id, author_id, primary_topic_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        topics.add_topic(primary_topic_id)

        await service.execute(
            CreateQuestionInput(
                community_id=community_id,
                author_id=author_id,
                primary_topic_id=primary_topic_id,
                title="Title",
                body="Body",
            )
        )
        assert uow.committed is True

    async def test_publishes_a_community_question_created_event(self) -> None:
        service, _, _, _, communities, topics, uow = _seeded()
        community_id, author_id, primary_topic_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        topics.add_topic(primary_topic_id)

        await service.execute(
            CreateQuestionInput(
                community_id=community_id,
                author_id=author_id,
                primary_topic_id=primary_topic_id,
                title="Title",
                body="Body",
            )
        )
        assert any(isinstance(e, CommunityQuestionCreated) for e in uow.published_events)

    async def test_stores_the_communitys_organization_id_on_the_question(self) -> None:
        service, questions, _, _, communities, topics, _ = _seeded()
        community_id, author_id, primary_topic_id = uuid4(), uuid4(), uuid4()
        summary = make_community_summary(community_id=community_id)
        communities.add_community(summary)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )
        topics.add_topic(primary_topic_id)

        output = await service.execute(
            CreateQuestionInput(
                community_id=community_id,
                author_id=author_id,
                primary_topic_id=primary_topic_id,
                title="Title",
                body="Body",
            )
        )
        stored = await questions.get_by_id(output.question_id)
        assert stored is not None
        assert stored.organization_id == summary.organization_id
