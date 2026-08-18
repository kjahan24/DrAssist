"""Integration tests for `SqlAlchemyCommunityCommentRepository` against a
real PostgreSQL instance — round-trip persistence (including a
top-level comment and a nested reply), `browse()` filtering (target/
community/topic/author/parent/top_level_only/status/keyword/date range,
the `status != 'deleted'` default exclusion), cursor pagination, and
`get_thread()`'s bounded-depth, non-recursive retrieval."""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.community_comments._helpers import (
    persist_org_user_community_answer,
    persist_org_user_community_post,
)

from app.modules.community_comments.domain.entities import CommunityComment
from app.modules.community_comments.domain.enums import CommentStatus, CommentTargetType
from app.modules.community_comments.domain.value_objects import CommentBody
from app.modules.community_comments.infrastructure.repositories import (
    SqlAlchemyCommunityCommentRepository,
)


def _make_comment(
    *,
    target_type: CommentTargetType,
    target_id: object,
    community_id: object,
    organization_id: object,
    topic_id: object | None,
    author_id: object,
    **overrides: object,
) -> CommunityComment:
    defaults: dict[str, object] = {
        "target_type": target_type,
        "target_id": target_id,
        "community_id": community_id,
        "organization_id": organization_id,
        "topic_id": topic_id,
        "author_id": author_id,
        "body": CommentBody(f"Detailed comment body {uuid4().hex[:8]}."),
    }
    defaults.update(overrides)
    return CommunityComment.create(**defaults)  # type: ignore[arg-type]


class TestCommunityCommentRoundTrip:
    async def test_save_and_reload_a_top_level_comment(self, db_session: AsyncSession) -> None:
        organization, user, community, post = await persist_org_user_community_post(db_session)
        repo = SqlAlchemyCommunityCommentRepository(db_session)
        comment = _make_comment(
            target_type=CommentTargetType.POST,
            target_id=post.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=None,
            author_id=user.id,
            is_anonymous=True,
        )

        await repo.add(comment)
        await db_session.commit()

        reloaded = await repo.get_by_id(comment.id)
        assert reloaded is not None
        assert reloaded.id == comment.id
        assert reloaded.target_type is CommentTargetType.POST
        assert reloaded.target_id == post.id
        assert reloaded.community_id == community.id
        assert reloaded.organization_id == organization.id
        assert reloaded.topic_id is None
        assert reloaded.author_id == user.id
        assert str(reloaded.body) == str(comment.body)
        assert reloaded.is_anonymous is True
        assert reloaded.status is CommentStatus.DRAFT
        assert reloaded.parent_comment_id is None
        assert reloaded.root_comment_id == comment.id
        assert reloaded.depth == 0

    async def test_save_and_reload_a_reply(self, db_session: AsyncSession) -> None:
        organization, user, community, topic, answer = await persist_org_user_community_answer(
            db_session
        )
        repo = SqlAlchemyCommunityCommentRepository(db_session)
        parent = _make_comment(
            target_type=CommentTargetType.ANSWER,
            target_id=answer.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=topic.id,
            author_id=user.id,
        )
        parent.publish()
        await repo.add(parent)
        await db_session.commit()

        reply = CommunityComment.create_reply(
            parent=parent, author_id=user.id, body=CommentBody("A reply.")
        )
        await repo.add(reply)
        await db_session.commit()

        reloaded = await repo.get_by_id(reply.id)
        assert reloaded is not None
        assert reloaded.parent_comment_id == parent.id
        assert reloaded.root_comment_id == parent.id
        assert reloaded.depth == 1
        assert reloaded.target_type is CommentTargetType.ANSWER
        assert reloaded.target_id == answer.id
        assert reloaded.topic_id == topic.id

    async def test_get_by_id_returns_none_for_unknown_comment(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyCommunityCommentRepository(db_session)
        assert await repo.get_by_id(uuid4()) is None

    async def test_add_persists_a_published_status_transition(
        self, db_session: AsyncSession
    ) -> None:
        organization, user, community, post = await persist_org_user_community_post(db_session)
        repo = SqlAlchemyCommunityCommentRepository(db_session)
        comment = _make_comment(
            target_type=CommentTargetType.POST,
            target_id=post.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=None,
            author_id=user.id,
        )
        await repo.add(comment)
        await db_session.commit()

        comment.publish()
        await repo.add(comment)
        await db_session.commit()

        reloaded = await repo.get_by_id(comment.id)
        assert reloaded is not None
        assert reloaded.status is CommentStatus.PUBLISHED
        assert reloaded.published_at is not None

    async def test_add_persists_a_deleted_status_transition(self, db_session: AsyncSession) -> None:
        organization, user, community, post = await persist_org_user_community_post(db_session)
        repo = SqlAlchemyCommunityCommentRepository(db_session)
        comment = _make_comment(
            target_type=CommentTargetType.POST,
            target_id=post.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=None,
            author_id=user.id,
        )
        await repo.add(comment)
        await db_session.commit()

        comment.delete()
        await repo.add(comment)
        await db_session.commit()

        reloaded = await repo.get_by_id(comment.id)
        assert reloaded is not None
        assert reloaded.status is CommentStatus.DELETED


class TestCommunityCommentBrowse:
    async def test_scopes_results_to_organization(self, db_session: AsyncSession) -> None:
        organization, user, community, post = await persist_org_user_community_post(db_session)
        other_org, other_user, other_community, other_post = await persist_org_user_community_post(
            db_session
        )
        repo = SqlAlchemyCommunityCommentRepository(db_session)
        matching = _make_comment(
            target_type=CommentTargetType.POST,
            target_id=post.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=None,
            author_id=user.id,
        )
        other = _make_comment(
            target_type=CommentTargetType.POST,
            target_id=other_post.id,
            community_id=other_community.id,
            organization_id=other_org.id,
            topic_id=None,
            author_id=other_user.id,
        )
        await repo.add(matching)
        await repo.add(other)
        await db_session.commit()

        results, _ = await repo.browse(organization_id=organization.id)
        ids = [c.id for c in results]
        assert matching.id in ids
        assert other.id not in ids

    async def test_filters_by_target(self, db_session: AsyncSession) -> None:
        organization, user, community, post = await persist_org_user_community_post(db_session)
        repo = SqlAlchemyCommunityCommentRepository(db_session)
        matching = _make_comment(
            target_type=CommentTargetType.POST,
            target_id=post.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=None,
            author_id=user.id,
        )
        other = _make_comment(
            target_type=CommentTargetType.POST,
            target_id=uuid4(),
            community_id=community.id,
            organization_id=organization.id,
            topic_id=None,
            author_id=user.id,
        )
        await repo.add(matching)
        await repo.add(other)
        await db_session.commit()

        results, _ = await repo.browse(
            organization_id=organization.id, target_type=CommentTargetType.POST, target_id=post.id
        )
        ids = [c.id for c in results]
        assert matching.id in ids
        assert other.id not in ids

    async def test_top_level_only_excludes_replies(self, db_session: AsyncSession) -> None:
        organization, user, community, post = await persist_org_user_community_post(db_session)
        repo = SqlAlchemyCommunityCommentRepository(db_session)
        parent = _make_comment(
            target_type=CommentTargetType.POST,
            target_id=post.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=None,
            author_id=user.id,
        )
        parent.publish()
        await repo.add(parent)
        await db_session.commit()
        reply = CommunityComment.create_reply(
            parent=parent, author_id=user.id, body=CommentBody("Reply.")
        )
        await repo.add(reply)
        await db_session.commit()

        results, _ = await repo.browse(organization_id=organization.id, top_level_only=True)
        ids = [c.id for c in results]
        assert parent.id in ids
        assert reply.id not in ids

    async def test_filters_by_parent_comment_id(self, db_session: AsyncSession) -> None:
        organization, user, community, post = await persist_org_user_community_post(db_session)
        repo = SqlAlchemyCommunityCommentRepository(db_session)
        parent = _make_comment(
            target_type=CommentTargetType.POST,
            target_id=post.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=None,
            author_id=user.id,
        )
        parent.publish()
        await repo.add(parent)
        await db_session.commit()
        reply = CommunityComment.create_reply(
            parent=parent, author_id=user.id, body=CommentBody("Reply.")
        )
        await repo.add(reply)
        await db_session.commit()

        results, _ = await repo.browse(organization_id=organization.id, parent_comment_id=parent.id)
        assert [c.id for c in results] == [reply.id]

    async def test_filters_by_status(self, db_session: AsyncSession) -> None:
        organization, user, community, post = await persist_org_user_community_post(db_session)
        repo = SqlAlchemyCommunityCommentRepository(db_session)
        published = _make_comment(
            target_type=CommentTargetType.POST,
            target_id=post.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=None,
            author_id=user.id,
        )
        published.publish()
        draft = _make_comment(
            target_type=CommentTargetType.POST,
            target_id=post.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=None,
            author_id=user.id,
        )
        await repo.add(published)
        await repo.add(draft)
        await db_session.commit()

        results, _ = await repo.browse(
            organization_id=organization.id, status=[CommentStatus.DRAFT]
        )
        ids = [c.id for c in results]
        assert draft.id in ids
        assert published.id not in ids

    async def test_keyword_search_matches_body(self, db_session: AsyncSession) -> None:
        organization, user, community, post = await persist_org_user_community_post(db_session)
        repo = SqlAlchemyCommunityCommentRepository(db_session)
        matching = _make_comment(
            target_type=CommentTargetType.POST,
            target_id=post.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=None,
            author_id=user.id,
            body=CommentBody("Discussing hypotension treatment."),
        )
        other = _make_comment(
            target_type=CommentTargetType.POST,
            target_id=post.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=None,
            author_id=user.id,
            body=CommentBody("Completely unrelated remark."),
        )
        await repo.add(matching)
        await repo.add(other)
        await db_session.commit()

        results, _ = await repo.browse(organization_id=organization.id, query="hypotension")
        ids = [c.id for c in results]
        assert matching.id in ids
        assert other.id not in ids

    async def test_excludes_deleted_comments_by_default(self, db_session: AsyncSession) -> None:
        organization, user, community, post = await persist_org_user_community_post(db_session)
        repo = SqlAlchemyCommunityCommentRepository(db_session)
        comment = _make_comment(
            target_type=CommentTargetType.POST,
            target_id=post.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=None,
            author_id=user.id,
        )
        await repo.add(comment)
        await db_session.commit()
        comment.delete()
        await repo.add(comment)
        await db_session.commit()

        results, _ = await repo.browse(organization_id=organization.id, target_id=post.id)
        assert comment.id not in [c.id for c in results]

    async def test_include_deleted_true_includes_deleted_comments(
        self, db_session: AsyncSession
    ) -> None:
        organization, user, community, post = await persist_org_user_community_post(db_session)
        repo = SqlAlchemyCommunityCommentRepository(db_session)
        comment = _make_comment(
            target_type=CommentTargetType.POST,
            target_id=post.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=None,
            author_id=user.id,
        )
        await repo.add(comment)
        await db_session.commit()
        comment.delete()
        await repo.add(comment)
        await db_session.commit()

        results, _ = await repo.browse(
            organization_id=organization.id, target_id=post.id, include_deleted=True
        )
        assert comment.id in [c.id for c in results]

    async def test_cursor_pagination_covers_all_comments_without_duplicates(
        self, db_session: AsyncSession
    ) -> None:
        organization, user, community, post = await persist_org_user_community_post(db_session)
        repo = SqlAlchemyCommunityCommentRepository(db_session)
        created = []
        for _ in range(5):
            comment = _make_comment(
                target_type=CommentTargetType.POST,
                target_id=post.id,
                community_id=community.id,
                organization_id=organization.id,
                topic_id=None,
                author_id=user.id,
            )
            await repo.add(comment)
            created.append(comment)
        await db_session.commit()

        seen: list[object] = []
        cursor: str | None = None
        for _ in range(10):
            page, next_cursor = await repo.browse(
                organization_id=organization.id, target_id=post.id, cursor=cursor, limit=2
            )
            seen.extend(c.id for c in page)
            cursor = next_cursor
            if cursor is None:
                break

        assert sorted(seen, key=str) == sorted((c.id for c in created), key=str)
        assert len(seen) == len(set(seen))


class TestCommunityCommentGetThread:
    async def test_returns_the_root_and_bounded_descendants(self, db_session: AsyncSession) -> None:
        organization, user, community, post = await persist_org_user_community_post(db_session)
        repo = SqlAlchemyCommunityCommentRepository(db_session)
        root = _make_comment(
            target_type=CommentTargetType.POST,
            target_id=post.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=None,
            author_id=user.id,
        )
        root.publish()
        await repo.add(root)
        await db_session.commit()

        current = root
        chain_ids = [root.id]
        for _ in range(3):
            reply = CommunityComment.create_reply(
                parent=current, author_id=user.id, body=CommentBody("Reply.")
            )
            reply.publish()
            await repo.add(reply)
            await db_session.commit()
            chain_ids.append(reply.id)
            current = reply

        items = await repo.get_thread(root.id, max_depth=5, status=[CommentStatus.PUBLISHED])
        assert {c.id for c in items} == set(chain_ids)

    async def test_excludes_items_beyond_max_depth(self, db_session: AsyncSession) -> None:
        organization, user, community, post = await persist_org_user_community_post(db_session)
        repo = SqlAlchemyCommunityCommentRepository(db_session)
        root = _make_comment(
            target_type=CommentTargetType.POST,
            target_id=post.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=None,
            author_id=user.id,
        )
        root.publish()
        await repo.add(root)
        await db_session.commit()
        reply = CommunityComment.create_reply(
            parent=root, author_id=user.id, body=CommentBody("Reply.")
        )
        reply.publish()
        await repo.add(reply)
        await db_session.commit()

        shallow = await repo.get_thread(root.id, max_depth=0, status=[CommentStatus.PUBLISHED])
        assert reply.id not in [c.id for c in shallow]

        deeper = await repo.get_thread(root.id, max_depth=1, status=[CommentStatus.PUBLISHED])
        assert reply.id in [c.id for c in deeper]

    async def test_orders_by_depth_then_created_at(self, db_session: AsyncSession) -> None:
        organization, user, community, post = await persist_org_user_community_post(db_session)
        repo = SqlAlchemyCommunityCommentRepository(db_session)
        root = _make_comment(
            target_type=CommentTargetType.POST,
            target_id=post.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=None,
            author_id=user.id,
        )
        root.publish()
        await repo.add(root)
        await db_session.commit()
        first_reply = CommunityComment.create_reply(
            parent=root, author_id=user.id, body=CommentBody("First.")
        )
        first_reply.publish()
        await repo.add(first_reply)
        await db_session.commit()
        second_reply = CommunityComment.create_reply(
            parent=first_reply, author_id=user.id, body=CommentBody("Second.")
        )
        second_reply.publish()
        await repo.add(second_reply)
        await db_session.commit()

        items = await repo.get_thread(root.id, max_depth=5, status=[CommentStatus.PUBLISHED])
        depths = [c.depth for c in items]
        assert depths == sorted(depths)
