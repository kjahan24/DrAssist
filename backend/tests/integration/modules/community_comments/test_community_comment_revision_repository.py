"""Integration tests for `SqlAlchemyCommunityCommentRevisionRepository`
against a real PostgreSQL instance — round-trip persistence, ordering by
`revision_number` descending, and confirming there is genuinely no
update/remove path through this repository (see its own docstring:
revision history is immutable, full stop).

`community_comment_revisions.comment_id`/`.author_id` are real foreign
keys (`-> community_comments.id`/`-> users.id`), so every revision here
is created against an actual persisted `CommunityComment` and `User`.
"""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.community_comments._helpers import (
    persist_org_user_community_post,
    persist_user,
)

from app.modules.community_comments.domain.entities import (
    CommunityComment,
    CommunityCommentRevision,
)
from app.modules.community_comments.domain.enums import CommentTargetType
from app.modules.community_comments.domain.repositories import CommunityCommentRevisionRepository
from app.modules.community_comments.domain.value_objects import CommentBody, CommentId
from app.modules.community_comments.infrastructure.repositories import (
    SqlAlchemyCommunityCommentRepository,
    SqlAlchemyCommunityCommentRevisionRepository,
)


async def _persist_comment(db_session: AsyncSession) -> tuple[CommunityComment, object]:
    organization, user, community, post = await persist_org_user_community_post(db_session)
    comments = SqlAlchemyCommunityCommentRepository(db_session)
    comment = CommunityComment.create(
        target_type=CommentTargetType.POST,
        target_id=post.id,
        community_id=community.id,
        organization_id=organization.id,
        topic_id=None,
        author_id=user.id,
        body=CommentBody("Original body."),
    )
    await comments.add(comment)
    await db_session.commit()
    return comment, organization.id


class TestCommunityCommentRevisionRoundTrip:
    async def test_save_and_reload_preserves_fields(self, db_session: AsyncSession) -> None:
        comment, organization_id = await _persist_comment(db_session)
        author = await persist_user(db_session, organization_id=organization_id)
        comment_id = CommentId(comment.id)
        repo = SqlAlchemyCommunityCommentRevisionRepository(db_session)
        revision = CommunityCommentRevision.create(
            comment_id=comment_id,
            revision_number=1,
            previous_body="The original comment body.",
            author_id=author.id,
        )

        await repo.add(revision)
        await db_session.commit()

        reloaded = await repo.get_by_id(revision.id)
        assert reloaded is not None
        assert reloaded.id == revision.id
        assert reloaded.comment_id == comment_id
        assert reloaded.revision_number == 1
        assert reloaded.previous_body == "The original comment body."
        assert reloaded.author_id == author.id

    async def test_get_by_id_returns_none_for_unknown_revision(
        self, db_session: AsyncSession
    ) -> None:
        repo = SqlAlchemyCommunityCommentRevisionRepository(db_session)
        assert await repo.get_by_id(uuid4()) is None

    async def test_repository_interface_exposes_no_remove_method(self) -> None:
        assert not hasattr(CommunityCommentRevisionRepository, "remove")
        assert not hasattr(SqlAlchemyCommunityCommentRevisionRepository, "remove")


class TestCommunityCommentRevisionListByComment:
    async def test_lists_only_revisions_for_the_requested_comment(
        self, db_session: AsyncSession
    ) -> None:
        comment, organization_id = await _persist_comment(db_session)
        other_comment, other_organization_id = await _persist_comment(db_session)
        author = await persist_user(db_session, organization_id=organization_id)
        other_author = await persist_user(db_session, organization_id=other_organization_id)
        repo = SqlAlchemyCommunityCommentRevisionRepository(db_session)
        mine = CommunityCommentRevision.create(
            comment_id=CommentId(comment.id),
            revision_number=1,
            previous_body="Mine.",
            author_id=author.id,
        )
        not_mine = CommunityCommentRevision.create(
            comment_id=CommentId(other_comment.id),
            revision_number=1,
            previous_body="Not mine.",
            author_id=other_author.id,
        )
        await repo.add(mine)
        await repo.add(not_mine)
        await db_session.commit()

        results = await repo.list_by_comment(comment.id)
        ids = [r.id for r in results]
        assert mine.id in ids
        assert not_mine.id not in ids

    async def test_orders_by_revision_number_descending(self, db_session: AsyncSession) -> None:
        comment, organization_id = await _persist_comment(db_session)
        author = await persist_user(db_session, organization_id=organization_id)
        repo = SqlAlchemyCommunityCommentRevisionRepository(db_session)
        for number in (1, 2, 3):
            revision = CommunityCommentRevision.create(
                comment_id=CommentId(comment.id),
                revision_number=number,
                previous_body=f"body {number}",
                author_id=author.id,
            )
            await repo.add(revision)
        await db_session.commit()

        results = await repo.list_by_comment(comment.id)
        assert [r.revision_number for r in results] == [3, 2, 1]

    async def test_respects_limit_and_offset(self, db_session: AsyncSession) -> None:
        comment, organization_id = await _persist_comment(db_session)
        author = await persist_user(db_session, organization_id=organization_id)
        repo = SqlAlchemyCommunityCommentRevisionRepository(db_session)
        for number in range(1, 4):
            revision = CommunityCommentRevision.create(
                comment_id=CommentId(comment.id),
                revision_number=number,
                previous_body=f"body {number}",
                author_id=author.id,
            )
            await repo.add(revision)
        await db_session.commit()

        results = await repo.list_by_comment(comment.id, offset=1, limit=1)
        assert len(results) == 1


class TestCommunityCommentUpdateContentPersistsARevision:
    """End-to-end workflow: editing a published comment's body persists
    both the updated live comment and its own archived revision
    snapshot, in the same shape `UpdateCommentService` performs."""

    async def test_editing_a_published_comment_persists_a_revision(
        self, db_session: AsyncSession
    ) -> None:
        organization, user, community, post = await persist_org_user_community_post(db_session)
        comments = SqlAlchemyCommunityCommentRepository(db_session)
        revisions = SqlAlchemyCommunityCommentRevisionRepository(db_session)
        comment = CommunityComment.create(
            target_type=CommentTargetType.POST,
            target_id=post.id,
            community_id=community.id,
            organization_id=organization.id,
            topic_id=None,
            author_id=user.id,
            body=CommentBody("Original body."),
        )
        comment.publish()
        await comments.add(comment)
        await db_session.commit()

        revision = comment.update_content(body=CommentBody("Edited body."))
        assert revision is not None
        await comments.add(comment)
        await revisions.add(revision)
        await db_session.commit()

        reloaded_comment = await comments.get_by_id(comment.id)
        reloaded_revisions = await revisions.list_by_comment(comment.id)
        assert reloaded_comment is not None
        assert str(reloaded_comment.body) == "Edited body."
        assert reloaded_comment.revision_number == 2
        assert len(reloaded_revisions) == 1
        assert reloaded_revisions[0].previous_body == "Original body."
