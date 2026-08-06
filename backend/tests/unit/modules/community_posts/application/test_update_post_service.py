"""Unit tests for `UpdatePostService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityRole
from app.modules.community_posts.application.dto import UpdatePostInput
from app.modules.community_posts.application.services.update_post_service import UpdatePostService
from app.modules.community_posts.domain.entities import CommunityPost
from app.modules.community_posts.domain.enums import PostType, PostVisibility
from app.modules.community_posts.domain.events import CommunityPostUpdated
from app.modules.community_posts.domain.exceptions import (
    InsufficientPostRoleError,
    PostNotFoundError,
)
from app.modules.community_posts.domain.value_objects import PostExcerpt, PostTitle
from tests.unit.modules.community_posts.application.fakes import (
    FakeCommunityPostRepository,
    FakeCommunityQueryPort,
    FakeUnitOfWork,
    make_community_summary,
    make_member_summary,
)


def _seeded() -> (
    tuple[UpdatePostService, FakeCommunityPostRepository, FakeCommunityQueryPort, FakeUnitOfWork]
):
    posts = FakeCommunityPostRepository()
    communities = FakeCommunityQueryPort()
    uow = FakeUnitOfWork()
    service = UpdatePostService(
        post_repository=posts, community_query_port=communities, unit_of_work=uow
    )
    return service, posts, communities, uow


async def _seed_post(
    posts: FakeCommunityPostRepository, communities: FakeCommunityQueryPort, **overrides: object
) -> CommunityPost:
    defaults: dict[str, object] = {
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "author_id": uuid4(),
        "title": PostTitle("Original Title"),
        "body": "Original body.",
    }
    defaults.update(overrides)
    post = CommunityPost.create(**defaults)  # type: ignore[arg-type]
    await posts.add(post)
    communities.add_community(make_community_summary(community_id=post.community_id))
    return post


class TestUpdatePost:
    async def test_author_updates_the_title(self) -> None:
        service, posts, communities, _ = _seeded()
        post = await _seed_post(posts, communities)

        await service.execute(
            UpdatePostInput(post_id=post.id, acting_user_id=post.author_id, title="New Title")
        )
        stored = await posts.get_by_id(post.id)
        assert stored is not None
        assert str(stored.title) == "New Title"

    async def test_author_updates_body(self) -> None:
        service, posts, communities, _ = _seeded()
        post = await _seed_post(posts, communities)

        await service.execute(
            UpdatePostInput(
                post_id=post.id, acting_user_id=post.author_id, body="New body content."
            )
        )
        stored = await posts.get_by_id(post.id)
        assert stored is not None
        assert stored.body == "New body content."

    async def test_moderator_can_update_someone_elses_post(self) -> None:
        service, posts, communities, _ = _seeded()
        post = await _seed_post(posts, communities)
        moderator_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=post.community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )

        await service.execute(
            UpdatePostInput(post_id=post.id, acting_user_id=moderator_id, title="Moderator Edit")
        )
        stored = await posts.get_by_id(post.id)
        assert stored is not None
        assert str(stored.title) == "Moderator Edit"

    async def test_plain_member_cannot_update_someone_elses_post(self) -> None:
        service, posts, communities, _ = _seeded()
        post = await _seed_post(posts, communities)
        member_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=post.community_id, user_id=member_id, role=CommunityRole.MEMBER
            )
        )

        with pytest.raises(InsufficientPostRoleError):
            await service.execute(
                UpdatePostInput(
                    post_id=post.id, acting_user_id=member_id, title="Unauthorized Edit"
                )
            )

    async def test_unknown_post_raises(self) -> None:
        service, _, _, _ = _seeded()
        with pytest.raises(PostNotFoundError):
            await service.execute(
                UpdatePostInput(post_id=uuid4(), acting_user_id=uuid4(), title="X")
            )

    async def test_updates_post_type_and_visibility(self) -> None:
        service, posts, communities, _ = _seeded()
        post = await _seed_post(posts, communities)

        await service.execute(
            UpdatePostInput(
                post_id=post.id,
                acting_user_id=post.author_id,
                post_type=PostType.RESEARCH,
                visibility=PostVisibility.MEMBERS_ONLY,
            )
        )
        stored = await posts.get_by_id(post.id)
        assert stored is not None
        assert stored.post_type is PostType.RESEARCH
        assert stored.visibility is PostVisibility.MEMBERS_ONLY

    async def test_commits_the_unit_of_work(self) -> None:
        service, posts, communities, uow = _seeded()
        post = await _seed_post(posts, communities)

        await service.execute(
            UpdatePostInput(post_id=post.id, acting_user_id=post.author_id, title="New Title")
        )
        assert uow.committed is True

    async def test_publishes_a_community_post_updated_event(self) -> None:
        service, posts, communities, uow = _seeded()
        post = await _seed_post(posts, communities)

        await service.execute(
            UpdatePostInput(post_id=post.id, acting_user_id=post.author_id, title="New Title")
        )
        assert any(isinstance(e, CommunityPostUpdated) for e in uow.published_events)

    async def test_output_reflects_the_update(self) -> None:
        service, posts, communities, _ = _seeded()
        post = await _seed_post(posts, communities)

        output = await service.execute(
            UpdatePostInput(post_id=post.id, acting_user_id=post.author_id, title="Renamed")
        )
        assert output.post_id == post.id
        assert output.title == "Renamed"

    async def test_explicit_excerpt_overrides_the_existing_one(self) -> None:
        service, posts, communities, _ = _seeded()
        post = await _seed_post(posts, communities)

        await service.execute(
            UpdatePostInput(
                post_id=post.id, acting_user_id=post.author_id, excerpt="A curated excerpt."
            )
        )
        stored = await posts.get_by_id(post.id)
        assert stored is not None
        assert str(stored.excerpt) == "A curated excerpt."

    async def test_editing_body_alone_leaves_the_existing_excerpt_untouched(self) -> None:
        service, posts, communities, _ = _seeded()
        post = await _seed_post(posts, communities, excerpt=PostExcerpt("Curated summary."))

        await service.execute(
            UpdatePostInput(post_id=post.id, acting_user_id=post.author_id, body="Brand new body.")
        )
        stored = await posts.get_by_id(post.id)
        assert stored is not None
        assert str(stored.excerpt) == "Curated summary."

    async def test_regenerate_excerpt_true_rederives_it_from_the_new_body(self) -> None:
        service, posts, communities, _ = _seeded()
        post = await _seed_post(posts, communities, excerpt=PostExcerpt("Stale excerpt."))

        await service.execute(
            UpdatePostInput(
                post_id=post.id,
                acting_user_id=post.author_id,
                body="A freshly written replacement body.",
                regenerate_excerpt=True,
            )
        )
        stored = await posts.get_by_id(post.id)
        assert stored is not None
        assert str(stored.excerpt) == "A freshly written replacement body."

    async def test_body_change_recomputes_read_time_minutes(self) -> None:
        service, posts, communities, _ = _seeded()
        post = await _seed_post(posts, communities)

        await service.execute(
            UpdatePostInput(
                post_id=post.id, acting_user_id=post.author_id, body=" ".join(["word"] * 400)
            )
        )
        stored = await posts.get_by_id(post.id)
        assert stored is not None
        assert stored.read_time_minutes == 2

    async def test_updates_is_anonymous(self) -> None:
        service, posts, communities, _ = _seeded()
        post = await _seed_post(posts, communities)

        await service.execute(
            UpdatePostInput(post_id=post.id, acting_user_id=post.author_id, is_anonymous=True)
        )
        stored = await posts.get_by_id(post.id)
        assert stored is not None
        assert stored.is_anonymous is True

    async def test_sets_the_featured_image(self) -> None:
        service, posts, communities, _ = _seeded()
        post = await _seed_post(posts, communities)
        document_id = uuid4()

        await service.execute(
            UpdatePostInput(
                post_id=post.id,
                acting_user_id=post.author_id,
                featured_image_document_id=document_id,
            )
        )
        stored = await posts.get_by_id(post.id)
        assert stored is not None
        assert stored.featured_image_document_id == document_id

    async def test_clears_the_featured_image(self) -> None:
        service, posts, communities, _ = _seeded()
        post = await _seed_post(posts, communities, featured_image_document_id=uuid4())

        await service.execute(
            UpdatePostInput(
                post_id=post.id, acting_user_id=post.author_id, clear_featured_image=True
            )
        )
        stored = await posts.get_by_id(post.id)
        assert stored is not None
        assert stored.featured_image_document_id is None

    async def test_tracks_updated_by(self) -> None:
        service, posts, communities, _ = _seeded()
        post = await _seed_post(posts, communities)

        await service.execute(
            UpdatePostInput(post_id=post.id, acting_user_id=post.author_id, title="New Title")
        )
        stored = await posts.get_by_id(post.id)
        assert stored is not None
        assert stored.updated_by == post.author_id
