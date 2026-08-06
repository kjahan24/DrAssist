"""Unit tests for `ManagePostTagsService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityRole
from app.modules.community_posts.application.dto import AssignPostTagInput, UnassignPostTagInput
from app.modules.community_posts.application.services.manage_post_tags_service import (
    ManagePostTagsService,
)
from app.modules.community_posts.domain.entities import CommunityPost
from app.modules.community_posts.domain.events import CommunityPostTagAssigned
from app.modules.community_posts.domain.exceptions import (
    DuplicatePostTagError,
    InsufficientPostRoleError,
    PostNotFoundError,
    PostTagNotFoundError,
)
from app.modules.community_posts.domain.value_objects import PostTitle
from tests.unit.modules.community_posts.application.fakes import (
    FakeCommunityPostRepository,
    FakeCommunityPostTagRepository,
    FakeCommunityQueryPort,
    FakeUnitOfWork,
    make_community_summary,
    make_member_summary,
)


def _seeded() -> (
    tuple[
        ManagePostTagsService,
        FakeCommunityPostRepository,
        FakeCommunityPostTagRepository,
        FakeCommunityQueryPort,
        FakeUnitOfWork,
    ]
):
    posts = FakeCommunityPostRepository()
    post_tags = FakeCommunityPostTagRepository()
    communities = FakeCommunityQueryPort()
    uow = FakeUnitOfWork()
    service = ManagePostTagsService(
        post_tag_repository=post_tags,
        post_repository=posts,
        community_query_port=communities,
        unit_of_work=uow,
    )
    return service, posts, post_tags, communities, uow


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


class TestAssignTag:
    async def test_author_assigns_a_tag(self) -> None:
        service, posts, post_tags, communities, _ = _seeded()
        post = await _seed_post(posts, communities)

        summary = await service.assign_tag(
            AssignPostTagInput(post_id=post.id, acting_user_id=post.author_id, tag="Oncology")
        )
        assert summary.tag == "oncology"
        assert len(await post_tags.list_by_post(post.id)) == 1

    async def test_plain_member_cannot_assign_tag_to_someone_elses_post(self) -> None:
        service, posts, _, communities, _ = _seeded()
        post = await _seed_post(posts, communities)
        member_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=post.community_id, user_id=member_id, role=CommunityRole.MEMBER
            )
        )

        with pytest.raises(InsufficientPostRoleError):
            await service.assign_tag(
                AssignPostTagInput(post_id=post.id, acting_user_id=member_id, tag="oncology")
            )

    async def test_unknown_post_raises(self) -> None:
        service, _, _, _, _ = _seeded()
        with pytest.raises(PostNotFoundError):
            await service.assign_tag(
                AssignPostTagInput(post_id=uuid4(), acting_user_id=uuid4(), tag="oncology")
            )

    async def test_duplicate_tag_raises(self) -> None:
        service, posts, _, communities, _ = _seeded()
        post = await _seed_post(posts, communities)
        await service.assign_tag(
            AssignPostTagInput(post_id=post.id, acting_user_id=post.author_id, tag="oncology")
        )

        with pytest.raises(DuplicatePostTagError):
            await service.assign_tag(
                AssignPostTagInput(post_id=post.id, acting_user_id=post.author_id, tag="Oncology")
            )

    async def test_commits_and_publishes_event(self) -> None:
        service, posts, _, communities, uow = _seeded()
        post = await _seed_post(posts, communities)

        await service.assign_tag(
            AssignPostTagInput(post_id=post.id, acting_user_id=post.author_id, tag="oncology")
        )
        assert uow.committed is True
        assert any(isinstance(e, CommunityPostTagAssigned) for e in uow.published_events)


class TestListTags:
    async def test_lists_assigned_tags(self) -> None:
        service, posts, _, communities, _ = _seeded()
        post = await _seed_post(posts, communities)
        await service.assign_tag(
            AssignPostTagInput(post_id=post.id, acting_user_id=post.author_id, tag="oncology")
        )

        result = await service.list_tags(post.id)
        assert [t.tag for t in result] == ["oncology"]

    async def test_returns_empty_for_a_post_with_no_assignments(self) -> None:
        service, posts, _, communities, _ = _seeded()
        post = await _seed_post(posts, communities)

        assert await service.list_tags(post.id) == []


class TestUnassignTag:
    async def test_author_unassigns_a_tag(self) -> None:
        service, posts, _, communities, _ = _seeded()
        post = await _seed_post(posts, communities)
        assignment = await service.assign_tag(
            AssignPostTagInput(post_id=post.id, acting_user_id=post.author_id, tag="oncology")
        )

        await service.unassign_tag(
            UnassignPostTagInput(
                post_id=post.id, acting_user_id=post.author_id, post_tag_id=assignment.post_tag_id
            )
        )
        assert await service.list_tags(post.id) == []

    async def test_moderator_unassigns_a_tag_from_someone_elses_post(self) -> None:
        service, posts, _, communities, _ = _seeded()
        post = await _seed_post(posts, communities)
        assignment = await service.assign_tag(
            AssignPostTagInput(post_id=post.id, acting_user_id=post.author_id, tag="oncology")
        )
        moderator_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=post.community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )

        await service.unassign_tag(
            UnassignPostTagInput(
                post_id=post.id, acting_user_id=moderator_id, post_tag_id=assignment.post_tag_id
            )
        )
        assert await service.list_tags(post.id) == []

    async def test_plain_member_cannot_unassign_tag_from_someone_elses_post(self) -> None:
        service, posts, _, communities, _ = _seeded()
        post = await _seed_post(posts, communities)
        assignment = await service.assign_tag(
            AssignPostTagInput(post_id=post.id, acting_user_id=post.author_id, tag="oncology")
        )
        member_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=post.community_id, user_id=member_id, role=CommunityRole.MEMBER
            )
        )

        with pytest.raises(InsufficientPostRoleError):
            await service.unassign_tag(
                UnassignPostTagInput(
                    post_id=post.id, acting_user_id=member_id, post_tag_id=assignment.post_tag_id
                )
            )

    async def test_unknown_assignment_raises(self) -> None:
        service, posts, _, communities, _ = _seeded()
        post = await _seed_post(posts, communities)

        with pytest.raises(PostTagNotFoundError):
            await service.unassign_tag(
                UnassignPostTagInput(
                    post_id=post.id, acting_user_id=post.author_id, post_tag_id=uuid4()
                )
            )
