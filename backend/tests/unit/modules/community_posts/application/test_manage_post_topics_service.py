"""Unit tests for `ManagePostTopicsService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityRole
from app.modules.community_posts.application.dto import (
    AssignPostTopicInput,
    UnassignPostTopicInput,
)
from app.modules.community_posts.application.services.manage_post_topics_service import (
    ManagePostTopicsService,
)
from app.modules.community_posts.domain.entities import CommunityPost
from app.modules.community_posts.domain.events import CommunityPostTopicAssigned
from app.modules.community_posts.domain.exceptions import (
    DuplicatePostTopicError,
    InsufficientPostRoleError,
    PostNotFoundError,
    PostTopicNotFoundError,
    TopicNotFoundForPostError,
)
from app.modules.community_posts.domain.value_objects import PostTitle
from tests.unit.modules.community_posts.application.fakes import (
    FakeCommunityPostRepository,
    FakeCommunityPostTopicRepository,
    FakeCommunityQueryPort,
    FakeTopicQueryPort,
    FakeUnitOfWork,
    make_community_summary,
    make_member_summary,
)


def _seeded() -> (
    tuple[
        ManagePostTopicsService,
        FakeCommunityPostRepository,
        FakeCommunityPostTopicRepository,
        FakeCommunityQueryPort,
        FakeTopicQueryPort,
        FakeUnitOfWork,
    ]
):
    posts = FakeCommunityPostRepository()
    post_topics = FakeCommunityPostTopicRepository()
    communities = FakeCommunityQueryPort()
    topics = FakeTopicQueryPort()
    uow = FakeUnitOfWork()
    service = ManagePostTopicsService(
        post_topic_repository=post_topics,
        post_repository=posts,
        community_query_port=communities,
        topic_query_port=topics,
        unit_of_work=uow,
    )
    return service, posts, post_topics, communities, topics, uow


async def _seed_post(
    posts: FakeCommunityPostRepository, communities: FakeCommunityQueryPort
) -> CommunityPost:
    post = CommunityPost.create(
        community_id=uuid4(),
        organization_id=uuid4(),
        author_id=uuid4(),
        title=PostTitle("Title"),
        body="Body",
    )
    await posts.add(post)
    communities.add_community(make_community_summary(community_id=post.community_id))
    return post


class TestAssignTopic:
    async def test_author_assigns_a_topic(self) -> None:
        service, posts, post_topics, communities, topics, _ = _seeded()
        post = await _seed_post(posts, communities)
        topic_id = uuid4()
        topics.add_topic(topic_id)

        summary = await service.assign_topic(
            AssignPostTopicInput(post_id=post.id, acting_user_id=post.author_id, topic_id=topic_id)
        )
        assert summary.topic_id == topic_id
        assert len(await post_topics.list_by_post(post.id)) == 1

    async def test_plain_member_cannot_assign_topic_to_someone_elses_post(self) -> None:
        service, posts, _, communities, topics, _ = _seeded()
        post = await _seed_post(posts, communities)
        topic_id = uuid4()
        topics.add_topic(topic_id)
        member_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=post.community_id, user_id=member_id, role=CommunityRole.MEMBER
            )
        )

        with pytest.raises(InsufficientPostRoleError):
            await service.assign_topic(
                AssignPostTopicInput(post_id=post.id, acting_user_id=member_id, topic_id=topic_id)
            )

    async def test_unknown_post_raises(self) -> None:
        service, _, _, _, topics, _ = _seeded()
        topic_id = uuid4()
        topics.add_topic(topic_id)
        with pytest.raises(PostNotFoundError):
            await service.assign_topic(
                AssignPostTopicInput(post_id=uuid4(), acting_user_id=uuid4(), topic_id=topic_id)
            )

    async def test_unknown_topic_raises(self) -> None:
        service, posts, _, communities, _, _ = _seeded()
        post = await _seed_post(posts, communities)

        with pytest.raises(TopicNotFoundForPostError):
            await service.assign_topic(
                AssignPostTopicInput(
                    post_id=post.id, acting_user_id=post.author_id, topic_id=uuid4()
                )
            )

    async def test_duplicate_assignment_raises(self) -> None:
        service, posts, _, communities, topics, _ = _seeded()
        post = await _seed_post(posts, communities)
        topic_id = uuid4()
        topics.add_topic(topic_id)
        await service.assign_topic(
            AssignPostTopicInput(post_id=post.id, acting_user_id=post.author_id, topic_id=topic_id)
        )

        with pytest.raises(DuplicatePostTopicError):
            await service.assign_topic(
                AssignPostTopicInput(
                    post_id=post.id, acting_user_id=post.author_id, topic_id=topic_id
                )
            )

    async def test_commits_and_publishes_event(self) -> None:
        service, posts, _, communities, topics, uow = _seeded()
        post = await _seed_post(posts, communities)
        topic_id = uuid4()
        topics.add_topic(topic_id)

        await service.assign_topic(
            AssignPostTopicInput(post_id=post.id, acting_user_id=post.author_id, topic_id=topic_id)
        )
        assert uow.committed is True
        assert any(isinstance(e, CommunityPostTopicAssigned) for e in uow.published_events)


class TestListTopics:
    async def test_lists_assigned_topics(self) -> None:
        service, posts, _, communities, topics, _ = _seeded()
        post = await _seed_post(posts, communities)
        topic_id = uuid4()
        topics.add_topic(topic_id)
        await service.assign_topic(
            AssignPostTopicInput(post_id=post.id, acting_user_id=post.author_id, topic_id=topic_id)
        )

        result = await service.list_topics(post.id)
        assert [t.topic_id for t in result] == [topic_id]

    async def test_returns_empty_for_a_post_with_no_assignments(self) -> None:
        service, posts, _, communities, _, _ = _seeded()
        post = await _seed_post(posts, communities)

        assert await service.list_topics(post.id) == []


class TestUnassignTopic:
    async def test_moderator_unassigns_a_topic_from_someone_elses_post(self) -> None:
        service, posts, _, communities, topics, _ = _seeded()
        post = await _seed_post(posts, communities)
        topic_id = uuid4()
        topics.add_topic(topic_id)
        assignment = await service.assign_topic(
            AssignPostTopicInput(post_id=post.id, acting_user_id=post.author_id, topic_id=topic_id)
        )
        moderator_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=post.community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )

        await service.unassign_topic(
            UnassignPostTopicInput(
                post_id=post.id, acting_user_id=moderator_id, post_topic_id=assignment.post_topic_id
            )
        )
        assert await service.list_topics(post.id) == []

    async def test_plain_member_cannot_unassign_topic_from_someone_elses_post(self) -> None:
        service, posts, _, communities, topics, _ = _seeded()
        post = await _seed_post(posts, communities)
        topic_id = uuid4()
        topics.add_topic(topic_id)
        assignment = await service.assign_topic(
            AssignPostTopicInput(post_id=post.id, acting_user_id=post.author_id, topic_id=topic_id)
        )
        member_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=post.community_id, user_id=member_id, role=CommunityRole.MEMBER
            )
        )

        with pytest.raises(InsufficientPostRoleError):
            await service.unassign_topic(
                UnassignPostTopicInput(
                    post_id=post.id,
                    acting_user_id=member_id,
                    post_topic_id=assignment.post_topic_id,
                )
            )

    async def test_author_unassigns_a_topic(self) -> None:
        service, posts, _, communities, topics, _ = _seeded()
        post = await _seed_post(posts, communities)
        topic_id = uuid4()
        topics.add_topic(topic_id)
        assignment = await service.assign_topic(
            AssignPostTopicInput(post_id=post.id, acting_user_id=post.author_id, topic_id=topic_id)
        )

        await service.unassign_topic(
            UnassignPostTopicInput(
                post_id=post.id,
                acting_user_id=post.author_id,
                post_topic_id=assignment.post_topic_id,
            )
        )
        assert await service.list_topics(post.id) == []

    async def test_unknown_assignment_raises(self) -> None:
        service, posts, _, communities, _, _ = _seeded()
        post = await _seed_post(posts, communities)

        with pytest.raises(PostTopicNotFoundError):
            await service.unassign_topic(
                UnassignPostTopicInput(
                    post_id=post.id, acting_user_id=post.author_id, post_topic_id=uuid4()
                )
            )
