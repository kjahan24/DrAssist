"""Unit tests for `CreatePostService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community_posts.application.dto import CreatePostInput
from app.modules.community_posts.application.services.create_post_service import CreatePostService
from app.modules.community_posts.domain.enums import PostStatus, PostType, PostVisibility
from app.modules.community_posts.domain.events import CommunityPostCreated
from app.modules.community_posts.domain.exceptions import (
    CommunityNotFoundForPostError,
    DuplicatePostTagError,
    DuplicatePostTopicError,
    PostMembershipRequiredError,
    TopicNotFoundForPostError,
)
from tests.unit.modules.community_posts.application.fakes import (
    FakeCommunityPostRepository,
    FakeCommunityPostTagRepository,
    FakeCommunityPostTopicRepository,
    FakeCommunityQueryPort,
    FakeTopicQueryPort,
    FakeUnitOfWork,
    make_community_summary,
    make_member_summary,
)


def _seeded() -> (
    tuple[
        CreatePostService,
        FakeCommunityPostRepository,
        FakeCommunityPostTopicRepository,
        FakeCommunityPostTagRepository,
        FakeCommunityQueryPort,
        FakeTopicQueryPort,
        FakeUnitOfWork,
    ]
):
    posts = FakeCommunityPostRepository()
    post_topics = FakeCommunityPostTopicRepository()
    post_tags = FakeCommunityPostTagRepository()
    communities = FakeCommunityQueryPort()
    topics = FakeTopicQueryPort()
    uow = FakeUnitOfWork()
    service = CreatePostService(
        post_repository=posts,
        post_topic_repository=post_topics,
        post_tag_repository=post_tags,
        community_query_port=communities,
        topic_query_port=topics,
        unit_of_work=uow,
    )
    return service, posts, post_topics, post_tags, communities, topics, uow


def _seed_membership(
    communities: FakeCommunityQueryPort, *, community_id: object, user_id: object
) -> None:
    communities.add_community(make_community_summary(community_id=community_id))
    communities.add_membership(make_member_summary(community_id=community_id, user_id=user_id))


class TestCreatePost:
    async def test_creates_a_post(self) -> None:
        service, posts, _, _, communities, _, _ = _seeded()
        community_id, author_id = uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)

        output = await service.execute(
            CreatePostInput(
                community_id=community_id,
                author_id=author_id,
                title="Cardiac Arrhythmia Tips",
                body="This is the body of the post.",
            )
        )

        stored = await posts.get_by_id(output.post_id)
        assert stored is not None
        assert str(stored.title) == "Cardiac Arrhythmia Tips"

    async def test_new_post_defaults_to_draft_status(self) -> None:
        service, _, _, _, communities, _, _ = _seeded()
        community_id, author_id = uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)

        output = await service.execute(
            CreatePostInput(
                community_id=community_id, author_id=author_id, title="Title", body="Body"
            )
        )
        assert output.status is PostStatus.DRAFT

    async def test_generates_a_slug_from_the_title(self) -> None:
        service, _, _, _, communities, _, _ = _seeded()
        community_id, author_id = uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)

        output = await service.execute(
            CreatePostInput(
                community_id=community_id, author_id=author_id, title="Hello World", body="Body"
            )
        )
        assert output.slug == "hello-world"

    async def test_duplicate_slug_within_the_same_community_is_disambiguated(self) -> None:
        service, _, _, _, communities, _, _ = _seeded()
        community_id, author_id = uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)

        first = await service.execute(
            CreatePostInput(
                community_id=community_id, author_id=author_id, title="Hello World", body="Body one"
            )
        )
        second = await service.execute(
            CreatePostInput(
                community_id=community_id, author_id=author_id, title="Hello World", body="Body two"
            )
        )
        assert first.slug != second.slug
        assert second.slug.startswith("hello-world")

    async def test_accepts_an_explicit_visibility(self) -> None:
        service, _, _, _, communities, _, _ = _seeded()
        community_id, author_id = uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)

        output = await service.execute(
            CreatePostInput(
                community_id=community_id,
                author_id=author_id,
                title="Title",
                body="Body",
                visibility=PostVisibility.PRIVATE,
            )
        )
        assert output.post_id is not None

    async def test_accepts_explicit_post_type(self) -> None:
        service, posts, _, _, communities, _, _ = _seeded()
        community_id, author_id = uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)

        output = await service.execute(
            CreatePostInput(
                community_id=community_id,
                author_id=author_id,
                title="Title",
                body="Body",
                post_type=PostType.CLINICAL_CASE,
            )
        )
        stored = await posts.get_by_id(output.post_id)
        assert stored is not None
        assert stored.post_type is PostType.CLINICAL_CASE

    async def test_assigns_initial_topics(self) -> None:
        service, _, post_topics, _, communities, topics, _ = _seeded()
        community_id, author_id, topic_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        topics.add_topic(topic_id)

        output = await service.execute(
            CreatePostInput(
                community_id=community_id,
                author_id=author_id,
                title="Title",
                body="Body",
                topic_ids=(topic_id,),
            )
        )
        assignments = await post_topics.list_by_post(output.post_id)
        assert [a.topic_id for a in assignments] == [topic_id]

    async def test_unknown_topic_id_raises(self) -> None:
        service, _, _, _, communities, _, _ = _seeded()
        community_id, author_id = uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)

        with pytest.raises(TopicNotFoundForPostError):
            await service.execute(
                CreatePostInput(
                    community_id=community_id,
                    author_id=author_id,
                    title="Title",
                    body="Body",
                    topic_ids=(uuid4(),),
                )
            )

    async def test_assigns_initial_tags(self) -> None:
        service, _, _, post_tags, communities, _, _ = _seeded()
        community_id, author_id = uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)

        output = await service.execute(
            CreatePostInput(
                community_id=community_id,
                author_id=author_id,
                title="Title",
                body="Body",
                tags=("diabetes", "insulin"),
            )
        )
        assignments = await post_tags.list_by_post(output.post_id)
        assert {a.tag for a in assignments} == {"diabetes", "insulin"}

    async def test_unknown_community_raises(self) -> None:
        service, _, _, _, _, _, _ = _seeded()
        with pytest.raises(CommunityNotFoundForPostError):
            await service.execute(
                CreatePostInput(community_id=uuid4(), author_id=uuid4(), title="Title", body="Body")
            )

    async def test_non_member_raises(self) -> None:
        service, _, _, _, communities, _, _ = _seeded()
        community_id = uuid4()
        communities.add_community(make_community_summary(community_id=community_id))

        with pytest.raises(PostMembershipRequiredError):
            await service.execute(
                CreatePostInput(
                    community_id=community_id, author_id=uuid4(), title="Title", body="Body"
                )
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, _, _, communities, _, uow = _seeded()
        community_id, author_id = uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)

        await service.execute(
            CreatePostInput(
                community_id=community_id, author_id=author_id, title="Title", body="Body"
            )
        )
        assert uow.committed is True

    async def test_publishes_a_community_post_created_event(self) -> None:
        service, _, _, _, communities, _, uow = _seeded()
        community_id, author_id = uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)

        await service.execute(
            CreatePostInput(
                community_id=community_id, author_id=author_id, title="Title", body="Body"
            )
        )
        assert any(isinstance(e, CommunityPostCreated) for e in uow.published_events)

    async def test_accepts_an_explicit_slug(self) -> None:
        service, _, _, _, communities, _, _ = _seeded()
        community_id, author_id = uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)

        output = await service.execute(
            CreatePostInput(
                community_id=community_id,
                author_id=author_id,
                title="Title",
                body="Body",
                slug="custom-slug",
            )
        )
        assert output.slug == "custom-slug"

    async def test_accepts_an_explicit_excerpt(self) -> None:
        service, posts, _, _, communities, _, _ = _seeded()
        community_id, author_id = uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)

        output = await service.execute(
            CreatePostInput(
                community_id=community_id,
                author_id=author_id,
                title="Title",
                body="Body",
                excerpt="A hand-written excerpt.",
            )
        )
        stored = await posts.get_by_id(output.post_id)
        assert stored is not None
        assert str(stored.excerpt) == "A hand-written excerpt."

    async def test_generates_an_excerpt_when_none_is_provided(self) -> None:
        service, posts, _, _, communities, _, _ = _seeded()
        community_id, author_id = uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)

        output = await service.execute(
            CreatePostInput(
                community_id=community_id,
                author_id=author_id,
                title="Title",
                body="This is the post body used to auto-derive an excerpt.",
            )
        )
        stored = await posts.get_by_id(output.post_id)
        assert stored is not None
        assert str(stored.excerpt) == "This is the post body used to auto-derive an excerpt."

    async def test_accepts_is_anonymous(self) -> None:
        service, posts, _, _, communities, _, _ = _seeded()
        community_id, author_id = uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)

        output = await service.execute(
            CreatePostInput(
                community_id=community_id,
                author_id=author_id,
                title="Title",
                body="Body",
                is_anonymous=True,
            )
        )
        stored = await posts.get_by_id(output.post_id)
        assert stored is not None
        assert stored.is_anonymous is True

    async def test_accepts_a_featured_image_document_id(self) -> None:
        service, posts, _, _, communities, _, _ = _seeded()
        community_id, author_id, document_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)

        output = await service.execute(
            CreatePostInput(
                community_id=community_id,
                author_id=author_id,
                title="Title",
                body="Body",
                featured_image_document_id=document_id,
            )
        )
        stored = await posts.get_by_id(output.post_id)
        assert stored is not None
        assert stored.featured_image_document_id == document_id

    async def test_stores_the_communitys_organization_id_on_the_post(self) -> None:
        service, posts, _, _, communities, _, _ = _seeded()
        community_id, author_id = uuid4(), uuid4()
        summary = make_community_summary(community_id=community_id)
        communities.add_community(summary)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        output = await service.execute(
            CreatePostInput(
                community_id=community_id, author_id=author_id, title="Title", body="Body"
            )
        )
        stored = await posts.get_by_id(output.post_id)
        assert stored is not None
        assert stored.organization_id == summary.organization_id

    async def test_duplicate_topic_id_in_initial_topics_raises(self) -> None:
        service, _, _, _, communities, topics, _ = _seeded()
        community_id, author_id, topic_id = uuid4(), uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)
        topics.add_topic(topic_id)

        with pytest.raises(DuplicatePostTopicError):
            await service.execute(
                CreatePostInput(
                    community_id=community_id,
                    author_id=author_id,
                    title="Title",
                    body="Body",
                    topic_ids=(topic_id, topic_id),
                )
            )

    async def test_duplicate_tag_in_initial_tags_raises(self) -> None:
        service, _, _, _, communities, _, _ = _seeded()
        community_id, author_id = uuid4(), uuid4()
        _seed_membership(communities, community_id=community_id, user_id=author_id)

        with pytest.raises(DuplicatePostTagError):
            await service.execute(
                CreatePostInput(
                    community_id=community_id,
                    author_id=author_id,
                    title="Title",
                    body="Body",
                    tags=("oncology", "Oncology"),
                )
            )
