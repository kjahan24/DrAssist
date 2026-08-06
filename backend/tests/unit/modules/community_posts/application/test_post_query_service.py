"""Unit tests for `GetPostService`/`ListPostsService`, using in-memory
fakes."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityMemberStatus, CommunityRole
from app.modules.community_posts.application.dto import ListPostsInput
from app.modules.community_posts.application.services.post_query_service import (
    GetPostService,
    ListPostsService,
)
from app.modules.community_posts.domain.entities import CommunityPost
from app.modules.community_posts.domain.enums import PostStatus, PostType, PostVisibility
from app.modules.community_posts.domain.exceptions import PostNotViewableError
from app.modules.community_posts.domain.value_objects import PostTitle
from tests.unit.modules.community_posts.application.fakes import (
    FakeCommunityPostRepository,
    FakeCommunityQueryPort,
    make_member_summary,
)


def _make_post(**overrides: object) -> CommunityPost:
    defaults: dict[str, object] = {
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "author_id": uuid4(),
        "title": PostTitle("Title"),
        "body": "Body",
    }
    defaults.update(overrides)
    return CommunityPost.create(**defaults)  # type: ignore[arg-type]


class TestGetPostById:
    async def test_returns_none_for_unknown_post(self) -> None:
        posts = FakeCommunityPostRepository()
        communities = FakeCommunityQueryPort()
        service = GetPostService(post_repository=posts, community_query_port=communities)

        result = await service.get_by_id(uuid4())
        assert result is None

    async def test_returns_a_public_post_with_no_acting_user(self) -> None:
        posts = FakeCommunityPostRepository()
        communities = FakeCommunityQueryPort()
        post = _make_post(visibility=PostVisibility.PUBLIC)
        await posts.add(post)
        service = GetPostService(post_repository=posts, community_query_port=communities)

        result = await service.get_by_id(post.id)
        assert result is not None
        assert result.post_id == post.id

    async def test_raises_when_members_only_post_viewed_by_non_member(self) -> None:
        posts = FakeCommunityPostRepository()
        communities = FakeCommunityQueryPort()
        post = _make_post(visibility=PostVisibility.MEMBERS_ONLY)
        await posts.add(post)
        service = GetPostService(post_repository=posts, community_query_port=communities)

        with pytest.raises(PostNotViewableError):
            await service.get_by_id(post.id, acting_user_id=uuid4())

    async def test_allows_members_only_post_for_active_member(self) -> None:
        posts = FakeCommunityPostRepository()
        communities = FakeCommunityQueryPort()
        post = _make_post(visibility=PostVisibility.MEMBERS_ONLY)
        await posts.add(post)
        viewer_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=post.community_id,
                user_id=viewer_id,
                role=CommunityRole.MEMBER,
                status=CommunityMemberStatus.ACTIVE,
            )
        )
        service = GetPostService(post_repository=posts, community_query_port=communities)

        result = await service.get_by_id(post.id, acting_user_id=viewer_id)
        assert result is not None

    async def test_private_post_viewable_by_author(self) -> None:
        posts = FakeCommunityPostRepository()
        communities = FakeCommunityQueryPort()
        post = _make_post(visibility=PostVisibility.PRIVATE)
        await posts.add(post)
        service = GetPostService(post_repository=posts, community_query_port=communities)

        result = await service.get_by_id(post.id, acting_user_id=post.author_id)
        assert result is not None

    async def test_private_post_not_viewable_by_plain_member(self) -> None:
        posts = FakeCommunityPostRepository()
        communities = FakeCommunityQueryPort()
        post = _make_post(visibility=PostVisibility.PRIVATE)
        await posts.add(post)
        viewer_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=post.community_id, user_id=viewer_id, role=CommunityRole.MEMBER
            )
        )
        service = GetPostService(post_repository=posts, community_query_port=communities)

        with pytest.raises(PostNotViewableError):
            await service.get_by_id(post.id, acting_user_id=viewer_id)

    async def test_private_post_viewable_by_moderator(self) -> None:
        posts = FakeCommunityPostRepository()
        communities = FakeCommunityQueryPort()
        post = _make_post(visibility=PostVisibility.PRIVATE)
        await posts.add(post)
        moderator_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=post.community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )
        service = GetPostService(post_repository=posts, community_query_port=communities)

        result = await service.get_by_id(post.id, acting_user_id=moderator_id)
        assert result is not None


class TestGetPostBySlug:
    async def test_returns_none_for_unknown_slug(self) -> None:
        posts = FakeCommunityPostRepository()
        communities = FakeCommunityQueryPort()
        service = GetPostService(post_repository=posts, community_query_port=communities)

        result = await service.get_by_slug(uuid4(), "does-not-exist")
        assert result is None

    async def test_returns_the_matching_public_post(self) -> None:
        posts = FakeCommunityPostRepository()
        communities = FakeCommunityQueryPort()
        post = _make_post(visibility=PostVisibility.PUBLIC)
        await posts.add(post)
        service = GetPostService(post_repository=posts, community_query_port=communities)

        result = await service.get_by_slug(post.community_id, str(post.slug))
        assert result is not None
        assert result.slug == str(post.slug)


class TestListPosts:
    async def test_lists_posts_scoped_to_organization(self) -> None:
        posts = FakeCommunityPostRepository()
        service = ListPostsService(post_repository=posts)
        org_id = uuid4()
        matching = _make_post(organization_id=org_id)
        other_org = _make_post()
        await posts.add(matching)
        await posts.add(other_org)

        result = await service.list_posts(ListPostsInput(organization_id=org_id))
        assert result.total == 1
        assert result.items[0].post_id == matching.id

    async def test_filters_by_community(self) -> None:
        posts = FakeCommunityPostRepository()
        service = ListPostsService(post_repository=posts)
        org_id = uuid4()
        community_id = uuid4()
        matching = _make_post(organization_id=org_id, community_id=community_id)
        other = _make_post(organization_id=org_id)
        await posts.add(matching)
        await posts.add(other)

        result = await service.list_posts(
            ListPostsInput(organization_id=org_id, community_id=community_id)
        )
        assert result.total == 1
        assert result.items[0].post_id == matching.id

    async def test_respects_limit(self) -> None:
        posts = FakeCommunityPostRepository()
        service = ListPostsService(post_repository=posts)
        org_id = uuid4()
        for _ in range(3):
            await posts.add(_make_post(organization_id=org_id))

        result = await service.list_posts(ListPostsInput(organization_id=org_id, limit=2))
        assert result.total == 3
        assert len(result.items) == 2

    async def test_filters_by_author(self) -> None:
        posts = FakeCommunityPostRepository()
        service = ListPostsService(post_repository=posts)
        org_id, author_id = uuid4(), uuid4()
        matching = _make_post(organization_id=org_id, author_id=author_id)
        other = _make_post(organization_id=org_id)
        await posts.add(matching)
        await posts.add(other)

        result = await service.list_posts(
            ListPostsInput(organization_id=org_id, author_id=author_id)
        )
        assert [i.post_id for i in result.items] == [matching.id]

    async def test_filters_by_post_type(self) -> None:
        posts = FakeCommunityPostRepository()
        service = ListPostsService(post_repository=posts)
        org_id = uuid4()
        matching = _make_post(organization_id=org_id, post_type=PostType.EDUCATIONAL)
        other = _make_post(organization_id=org_id, post_type=PostType.DISCUSSION)
        await posts.add(matching)
        await posts.add(other)

        result = await service.list_posts(
            ListPostsInput(organization_id=org_id, post_type=(PostType.EDUCATIONAL,))
        )
        assert [i.post_id for i in result.items] == [matching.id]

    async def test_filters_by_status(self) -> None:
        posts = FakeCommunityPostRepository()
        service = ListPostsService(post_repository=posts)
        org_id = uuid4()
        published = _make_post(organization_id=org_id)
        published.publish()
        draft = _make_post(organization_id=org_id)
        await posts.add(published)
        await posts.add(draft)

        result = await service.list_posts(
            ListPostsInput(organization_id=org_id, status=(PostStatus.DRAFT,))
        )
        assert [i.post_id for i in result.items] == [draft.id]

    async def test_filters_by_visibility(self) -> None:
        posts = FakeCommunityPostRepository()
        service = ListPostsService(post_repository=posts)
        org_id = uuid4()
        matching = _make_post(organization_id=org_id, visibility=PostVisibility.MEMBERS_ONLY)
        other = _make_post(organization_id=org_id, visibility=PostVisibility.PUBLIC)
        await posts.add(matching)
        await posts.add(other)

        result = await service.list_posts(
            ListPostsInput(organization_id=org_id, visibility=(PostVisibility.MEMBERS_ONLY,))
        )
        assert [i.post_id for i in result.items] == [matching.id]

    async def test_filters_pinned_only(self) -> None:
        posts = FakeCommunityPostRepository()
        service = ListPostsService(post_repository=posts)
        org_id = uuid4()
        pinned = _make_post(organization_id=org_id)
        pinned.set_pinned(True)
        other = _make_post(organization_id=org_id)
        await posts.add(pinned)
        await posts.add(other)

        result = await service.list_posts(ListPostsInput(organization_id=org_id, pinned_only=True))
        assert [i.post_id for i in result.items] == [pinned.id]

    async def test_filters_featured_only(self) -> None:
        posts = FakeCommunityPostRepository()
        service = ListPostsService(post_repository=posts)
        org_id = uuid4()
        featured = _make_post(organization_id=org_id)
        featured.set_featured(True)
        other = _make_post(organization_id=org_id)
        await posts.add(featured)
        await posts.add(other)

        result = await service.list_posts(
            ListPostsInput(organization_id=org_id, featured_only=True)
        )
        assert [i.post_id for i in result.items] == [featured.id]

    async def test_respects_offset(self) -> None:
        posts = FakeCommunityPostRepository()
        service = ListPostsService(post_repository=posts)
        org_id = uuid4()
        for _ in range(3):
            await posts.add(_make_post(organization_id=org_id))

        result = await service.list_posts(ListPostsInput(organization_id=org_id, limit=2, offset=2))
        assert result.total == 3
        assert len(result.items) == 1

    async def test_sort_order_ascending_reverses_the_default_order(self) -> None:
        posts = FakeCommunityPostRepository()
        service = ListPostsService(post_repository=posts)
        org_id = uuid4()
        first = _make_post(organization_id=org_id)
        second = _make_post(organization_id=org_id)
        await posts.add(first)
        await posts.add(second)

        descending = await service.list_posts(
            ListPostsInput(organization_id=org_id, sort_order="desc")
        )
        ascending = await service.list_posts(
            ListPostsInput(organization_id=org_id, sort_order="asc")
        )
        assert [i.post_id for i in ascending.items] == list(
            reversed([i.post_id for i in descending.items])
        )
