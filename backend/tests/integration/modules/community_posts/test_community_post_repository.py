"""Integration tests for `SqlAlchemyCommunityPostRepository` against a
real PostgreSQL instance — round-trip persistence, `search()` filtering,
and `browse_feed()` cursor (keyset) pagination including the
`pinned_first=True` behavior."""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.community_posts._helpers import persist_org_user_community

from app.modules.community_posts.domain.entities import CommunityPost
from app.modules.community_posts.domain.enums import PostStatus, PostType, PostVisibility
from app.modules.community_posts.domain.value_objects import PostTitle
from app.modules.community_posts.infrastructure.repositories import (
    SqlAlchemyCommunityPostRepository,
)


def _make_post(
    *, community_id: object, organization_id: object, author_id: object, **overrides: object
) -> CommunityPost:
    defaults: dict[str, object] = {
        "community_id": community_id,
        "organization_id": organization_id,
        "author_id": author_id,
        "title": PostTitle(f"A Clinical Case {uuid4().hex[:8]}"),
        "body": "Detailed clinical case body.",
    }
    defaults.update(overrides)
    return CommunityPost.create(**defaults)  # type: ignore[arg-type]


class TestCommunityPostRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        repo = SqlAlchemyCommunityPostRepository(db_session)
        post = _make_post(
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            post_type=PostType.CLINICAL_CASE,
            visibility=PostVisibility.MEMBERS_ONLY,
        )

        await repo.add(post)
        await db_session.commit()

        reloaded = await repo.get_by_id(post.id)
        assert reloaded is not None
        assert reloaded.id == post.id
        assert reloaded.community_id == community.id
        assert reloaded.organization_id == organization.id
        assert reloaded.author_id == user.id
        assert str(reloaded.slug) == str(post.slug)
        assert reloaded.title.value == post.title.value
        assert reloaded.post_type is PostType.CLINICAL_CASE
        assert reloaded.visibility is PostVisibility.MEMBERS_ONLY
        assert reloaded.status is PostStatus.DRAFT
        assert reloaded.read_time_minutes >= 1

    async def test_get_by_id_returns_none_for_unknown_post(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyCommunityPostRepository(db_session)
        assert await repo.get_by_id(uuid4()) is None

    async def test_get_by_slug_finds_the_matching_post(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        repo = SqlAlchemyCommunityPostRepository(db_session)
        post = _make_post(
            community_id=community.id, organization_id=organization.id, author_id=user.id
        )
        await repo.add(post)
        await db_session.commit()

        reloaded = await repo.get_by_slug(community.id, str(post.slug))
        assert reloaded is not None
        assert reloaded.id == post.id

    async def test_remove_soft_deletes_the_post(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        repo = SqlAlchemyCommunityPostRepository(db_session)
        post = _make_post(
            community_id=community.id, organization_id=organization.id, author_id=user.id
        )
        await repo.add(post)
        await db_session.commit()

        await repo.remove(post.id)
        await db_session.commit()

        assert await repo.get_by_id(post.id) is None


class TestCommunityPostSearch:
    async def test_scopes_results_to_organization(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        other_org, other_user, other_community = await persist_org_user_community(db_session)
        repo = SqlAlchemyCommunityPostRepository(db_session)
        matching = _make_post(
            community_id=community.id, organization_id=organization.id, author_id=user.id
        )
        other = _make_post(
            community_id=other_community.id, organization_id=other_org.id, author_id=other_user.id
        )
        await repo.add(matching)
        await repo.add(other)
        await db_session.commit()

        results, total = await repo.search(organization_id=organization.id)
        ids = [p.id for p in results]
        assert matching.id in ids
        assert other.id not in ids
        assert total >= 1

    async def test_filters_by_post_type(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        repo = SqlAlchemyCommunityPostRepository(db_session)
        clinical = _make_post(
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            post_type=PostType.CLINICAL_CASE,
        )
        discussion = _make_post(
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            post_type=PostType.DISCUSSION,
        )
        await repo.add(clinical)
        await repo.add(discussion)
        await db_session.commit()

        results, _ = await repo.search(
            organization_id=organization.id,
            community_id=community.id,
            post_type=[PostType.CLINICAL_CASE],
        )
        ids = [p.id for p in results]
        assert clinical.id in ids
        assert discussion.id not in ids

    async def test_keyword_search_matches_title(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        repo = SqlAlchemyCommunityPostRepository(db_session)
        matching = _make_post(
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            title=PostTitle("Managing Hypertension"),
        )
        other = _make_post(
            community_id=community.id,
            organization_id=organization.id,
            author_id=user.id,
            title=PostTitle("Unrelated Topic"),
        )
        await repo.add(matching)
        await repo.add(other)
        await db_session.commit()

        results, _ = await repo.search(
            organization_id=organization.id, community_id=community.id, query="Hypertension"
        )
        ids = [p.id for p in results]
        assert matching.id in ids
        assert other.id not in ids

    async def test_excludes_soft_deleted_posts_by_default(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        repo = SqlAlchemyCommunityPostRepository(db_session)
        post = _make_post(
            community_id=community.id, organization_id=organization.id, author_id=user.id
        )
        await repo.add(post)
        await db_session.commit()
        await repo.remove(post.id)
        await db_session.commit()

        results, _ = await repo.search(organization_id=organization.id, community_id=community.id)
        assert post.id not in [p.id for p in results]


class TestCommunityPostBrowseFeed:
    async def test_returns_only_published_posts(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        repo = SqlAlchemyCommunityPostRepository(db_session)
        published = _make_post(
            community_id=community.id, organization_id=organization.id, author_id=user.id
        )
        published.publish()
        draft = _make_post(
            community_id=community.id, organization_id=organization.id, author_id=user.id
        )
        await repo.add(published)
        await repo.add(draft)
        await db_session.commit()

        items, _ = await repo.browse_feed(
            organization_id=organization.id, community_id=community.id
        )
        ids = [p.id for p in items]
        assert published.id in ids
        assert draft.id not in ids

    async def test_pinned_post_surfaces_first_on_first_page(self, db_session: AsyncSession) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        repo = SqlAlchemyCommunityPostRepository(db_session)
        regular = _make_post(
            community_id=community.id, organization_id=organization.id, author_id=user.id
        )
        regular.publish()
        pinned = _make_post(
            community_id=community.id, organization_id=organization.id, author_id=user.id
        )
        pinned.publish()
        pinned.set_pinned(True)
        await repo.add(regular)
        await repo.add(pinned)
        await db_session.commit()

        items, _ = await repo.browse_feed(
            organization_id=organization.id, community_id=community.id, pinned_first=True
        )
        assert items[0].id == pinned.id

    async def test_cursor_pagination_covers_all_posts_without_duplicates(
        self, db_session: AsyncSession
    ) -> None:
        organization, user, community = await persist_org_user_community(db_session)
        repo = SqlAlchemyCommunityPostRepository(db_session)
        created = []
        for _ in range(5):
            post = _make_post(
                community_id=community.id, organization_id=organization.id, author_id=user.id
            )
            post.publish()
            await repo.add(post)
            created.append(post)
        await db_session.commit()

        seen: list[object] = []
        cursor: str | None = None
        for _ in range(10):
            page, next_cursor = await repo.browse_feed(
                organization_id=organization.id, community_id=community.id, cursor=cursor, limit=2
            )
            seen.extend(p.id for p in page)
            cursor = next_cursor
            if cursor is None:
                break

        assert sorted(seen, key=str) == sorted((p.id for p in created), key=str)
        assert len(seen) == len(set(seen))
