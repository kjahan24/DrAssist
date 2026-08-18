"""Unit tests for `UpdateCommentService`, using in-memory fakes. Used
uniformly for both top-level comments and replies — this test file
exercises it against a top-level comment; `test_create_reply_service.py`
already confirms a reply is a plain `CommunityComment` row, so there is
nothing reply-specific left to additionally test here."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityRole
from app.modules.community_comments.application.dto import UpdateCommentInput
from app.modules.community_comments.application.services.update_comment_service import (
    UpdateCommentService,
)
from app.modules.community_comments.domain.entities import CommunityComment
from app.modules.community_comments.domain.enums import CommentTargetType
from app.modules.community_comments.domain.exceptions import (
    CommentNotFoundError,
    InsufficientCommentRoleError,
)
from app.modules.community_comments.domain.value_objects import CommentBody
from tests.unit.modules.community_comments.application.fakes import (
    FakeCommunityCommentRepository,
    FakeCommunityCommentRevisionRepository,
    FakeCommunityQueryPort,
    FakeUnitOfWork,
    make_member_summary,
)


def _seeded() -> (
    tuple[
        UpdateCommentService,
        FakeCommunityCommentRepository,
        FakeCommunityCommentRevisionRepository,
        FakeCommunityQueryPort,
        FakeUnitOfWork,
    ]
):
    comments = FakeCommunityCommentRepository()
    revisions = FakeCommunityCommentRevisionRepository()
    communities = FakeCommunityQueryPort()
    uow = FakeUnitOfWork()
    service = UpdateCommentService(
        comment_repository=comments,
        comment_revision_repository=revisions,
        community_query_port=communities,
        unit_of_work=uow,
    )
    return service, comments, revisions, communities, uow


async def _seed_comment(
    comments: FakeCommunityCommentRepository,
    *,
    author_id: object,
    community_id: object,
    published: bool = False,
) -> CommunityComment:
    comment = CommunityComment.create(
        target_type=CommentTargetType.POST,
        target_id=uuid4(),
        community_id=community_id,  # type: ignore[arg-type]
        organization_id=uuid4(),
        topic_id=None,
        author_id=author_id,  # type: ignore[arg-type]
        body=CommentBody("Original body."),
    )
    if published:
        comment.publish()
    comment.pull_events()
    await comments.add(comment)
    return comment


class TestUpdateComment:
    async def test_updates_the_body(self) -> None:
        service, comments, _, communities, _ = _seeded()
        author_id, community_id = uuid4(), uuid4()
        comment = await _seed_comment(comments, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        await service.execute(
            UpdateCommentInput(comment_id=comment.id, acting_user_id=author_id, body="New body.")
        )
        stored = await comments.get_by_id(comment.id)
        assert stored is not None
        assert str(stored.body) == "New body."

    async def test_editing_a_draft_creates_no_revision(self) -> None:
        service, comments, revisions, communities, _ = _seeded()
        author_id, community_id = uuid4(), uuid4()
        comment = await _seed_comment(comments, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        output = await service.execute(
            UpdateCommentInput(comment_id=comment.id, acting_user_id=author_id, body="New body.")
        )
        assert output.revision_number == 1
        assert await revisions.list_by_comment(comment.id) == []

    async def test_editing_a_published_comment_creates_a_revision(self) -> None:
        service, comments, revisions, communities, _ = _seeded()
        author_id, community_id = uuid4(), uuid4()
        comment = await _seed_comment(
            comments, author_id=author_id, community_id=community_id, published=True
        )
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        await service.execute(
            UpdateCommentInput(comment_id=comment.id, acting_user_id=author_id, body="Edited body.")
        )
        stored_revisions = await revisions.list_by_comment(comment.id)
        assert len(stored_revisions) == 1
        assert stored_revisions[0].previous_body == "Original body."

    async def test_moderator_may_update_another_authors_comment(self) -> None:
        service, comments, _, communities, _ = _seeded()
        author_id, moderator_id, community_id = uuid4(), uuid4(), uuid4()
        comment = await _seed_comment(comments, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )

        await service.execute(
            UpdateCommentInput(
                comment_id=comment.id, acting_user_id=moderator_id, body="Moderated edit."
            )
        )
        stored = await comments.get_by_id(comment.id)
        assert stored is not None
        assert str(stored.body) == "Moderated edit."

    async def test_plain_member_cannot_update_another_authors_comment(self) -> None:
        service, comments, _, communities, _ = _seeded()
        author_id, other_id, community_id = uuid4(), uuid4(), uuid4()
        comment = await _seed_comment(comments, author_id=author_id, community_id=community_id)
        communities.add_membership(make_member_summary(community_id=community_id, user_id=other_id))

        with pytest.raises(InsufficientCommentRoleError):
            await service.execute(
                UpdateCommentInput(
                    comment_id=comment.id, acting_user_id=other_id, body="Not allowed."
                )
            )

    async def test_unknown_comment_raises(self) -> None:
        service, _, _, _, _ = _seeded()
        with pytest.raises(CommentNotFoundError):
            await service.execute(
                UpdateCommentInput(comment_id=uuid4(), acting_user_id=uuid4(), body="Body.")
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, comments, _, communities, uow = _seeded()
        author_id, community_id = uuid4(), uuid4()
        comment = await _seed_comment(comments, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        await service.execute(
            UpdateCommentInput(comment_id=comment.id, acting_user_id=author_id, body="New body.")
        )
        assert uow.committed is True
