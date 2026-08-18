"""Unit tests for `CommentRevisionQueryService` — read-only, no
create/remove seam; see `CommunityCommentRevisionRepository`'s own
docstring for why."""

from uuid import uuid4

from app.modules.community_comments.application.services.comment_revision_query_service import (
    CommentRevisionQueryService,
)
from app.modules.community_comments.domain.entities import CommunityCommentRevision
from app.modules.community_comments.domain.value_objects import CommentId
from tests.unit.modules.community_comments.application.fakes import (
    FakeCommunityCommentRevisionRepository,
)


class TestListRevisions:
    async def test_returns_empty_list_for_a_comment_with_no_revisions(self) -> None:
        revisions = FakeCommunityCommentRevisionRepository()
        service = CommentRevisionQueryService(comment_revision_repository=revisions)

        result = await service.list_revisions(uuid4())
        assert result == []

    async def test_lists_revisions_for_a_comment(self) -> None:
        revisions = FakeCommunityCommentRevisionRepository()
        service = CommentRevisionQueryService(comment_revision_repository=revisions)
        comment_id = uuid4()
        revision = CommunityCommentRevision.create(
            comment_id=CommentId(comment_id),
            revision_number=1,
            previous_body="Old body.",
            author_id=uuid4(),
        )
        await revisions.add(revision)

        result = await service.list_revisions(comment_id)
        assert len(result) == 1
        assert result[0].previous_body == "Old body."

    async def test_only_returns_revisions_for_the_requested_comment(self) -> None:
        revisions = FakeCommunityCommentRevisionRepository()
        service = CommentRevisionQueryService(comment_revision_repository=revisions)
        comment_id, other_comment_id = uuid4(), uuid4()
        await revisions.add(
            CommunityCommentRevision.create(
                comment_id=CommentId(comment_id),
                revision_number=1,
                previous_body="Mine.",
                author_id=uuid4(),
            )
        )
        await revisions.add(
            CommunityCommentRevision.create(
                comment_id=CommentId(other_comment_id),
                revision_number=1,
                previous_body="Not mine.",
                author_id=uuid4(),
            )
        )

        result = await service.list_revisions(comment_id)
        assert len(result) == 1
        assert result[0].previous_body == "Mine."

    async def test_orders_by_revision_number_descending(self) -> None:
        revisions = FakeCommunityCommentRevisionRepository()
        service = CommentRevisionQueryService(comment_revision_repository=revisions)
        comment_id = uuid4()
        for number in (1, 2, 3):
            await revisions.add(
                CommunityCommentRevision.create(
                    comment_id=CommentId(comment_id),
                    revision_number=number,
                    previous_body=f"body {number}",
                    author_id=uuid4(),
                )
            )

        result = await service.list_revisions(comment_id)
        assert [r.revision_number for r in result] == [3, 2, 1]

    async def test_respects_limit_and_offset(self) -> None:
        revisions = FakeCommunityCommentRevisionRepository()
        service = CommentRevisionQueryService(comment_revision_repository=revisions)
        comment_id = uuid4()
        for number in range(1, 4):
            await revisions.add(
                CommunityCommentRevision.create(
                    comment_id=CommentId(comment_id),
                    revision_number=number,
                    previous_body=f"body {number}",
                    author_id=uuid4(),
                )
            )

        result = await service.list_revisions(comment_id, offset=1, limit=1)
        assert len(result) == 1
